import logging
from celery import shared_task
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def _send_ws(job_id, data: dict):
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'patch_{job_id}',
            {'type': 'patch.progress', **data},
        )


@shared_task(bind=True)
def run_patch_job(self, job_id: int):
    from .models import PatchJob
    from apps.clusters.models import Node
    from apps.clusters.talosctl import TalosctlRunner

    try:
        job = PatchJob.objects.select_related('cluster').prefetch_related('target_nodes').get(pk=job_id)
    except PatchJob.DoesNotExist:
        logger.error('run_patch_job: job %s not found', job_id)
        return {'job_id': job_id, 'status': 'not_found'}
    job.status = PatchJob.STATUS_RUNNING
    job.started_at = timezone.now()
    job.celery_task_id = self.request.id
    job.save(update_fields=['status', 'started_at', 'celery_task_id'])

    # Resolve target nodes
    nodes = list(job.target_nodes.all())
    if not nodes:
        qs = job.cluster.nodes.all()
        if job.target_role == 'controlplane':
            qs = qs.filter(role='controlplane')
        elif job.target_role == 'worker':
            qs = qs.filter(role='worker')
        nodes = list(qs)

    success_count = 0
    fail_count = 0

    try:
        with TalosctlRunner(job.cluster) as t:
            for node in nodes:
                msg = f'[{node.ip_address}] Applying patch...'
                logger.info(msg)
                job.append_log(msg)
                _send_ws(job_id, {'node': node.ip_address, 'status': 'patching', 'message': msg})

                result = t.patch_machineconfig(node.ip_address, job.patch_content)

                output = (result.get('stdout') or '') + (result.get('stderr') or '')
                if output.strip():
                    job.append_log(output.strip())
                    _send_ws(job_id, {'node': node.ip_address, 'status': 'patching', 'message': output.strip()})

                if result['success']:
                    success_count += 1
                    msg = f'[{node.ip_address}] Patch applied successfully.'
                    _send_ws(job_id, {'node': node.ip_address, 'status': 'success', 'message': msg})
                else:
                    fail_count += 1
                    msg = f'[{node.ip_address}] Patch FAILED: {result.get("stderr", "").strip()}'
                    logger.error(msg)
                    _send_ws(job_id, {'node': node.ip_address, 'status': 'failed', 'message': msg})
                job.append_log(msg)

    except Exception as exc:
        logger.exception(f'Patch job {job_id} raised an exception')
        job.append_log(f'EXCEPTION: {exc}')
        job.status = PatchJob.STATUS_FAILED
    else:
        if fail_count == 0:
            job.status = PatchJob.STATUS_SUCCESS
        elif success_count == 0:
            job.status = PatchJob.STATUS_FAILED
        else:
            job.status = PatchJob.STATUS_PARTIAL
    finally:
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'completed_at'])
        _send_ws(job_id, {
            'status': job.status,
            'message': f'Job finished: {job.status}',
            'done': True,
        })

    return {'job_id': job_id, 'status': job.status}
