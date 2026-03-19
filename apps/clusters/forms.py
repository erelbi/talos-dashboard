import ipaddress

import yaml
from django import forms
from .models import Cluster, Node


class ClusterForm(forms.ModelForm):
    class Meta:
        model = Cluster
        fields = ['name', 'endpoint', 'talosconfig_content']
        widgets = {
            'talosconfig_content': forms.Textarea(attrs={
                'rows': 20,
                'class': 'font-monospace',
                'placeholder': 'Paste your talosconfig YAML content here...',
            }),
            'endpoint': forms.TextInput(attrs={
                'placeholder': '192.168.1.10  or  192.168.1.10:50000',
            }),
        }

    def clean_endpoint(self):
        endpoint = self.cleaned_data.get('endpoint', '').strip()
        # Strip protocol if user pasted it
        endpoint = endpoint.replace('https://', '').replace('http://', '').rstrip('/')
        if not endpoint:
            raise forms.ValidationError('Endpoint cannot be empty.')
        return endpoint

    def clean_talosconfig_content(self):
        content = self.cleaned_data.get('talosconfig_content', '')
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n').strip()
        if not content:
            raise forms.ValidationError('Talosconfig content cannot be empty.')
        # Basic YAML sanity check
        if 'context' not in content and 'contexts' not in content:
            raise forms.ValidationError(
                'This does not appear to be a valid talosconfig (missing "context" key).'
            )
        # Validate it's parseable YAML
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise forms.ValidationError(f'Invalid YAML: {e}')
        return content


class NodeForm(forms.ModelForm):
    class Meta:
        model = Node
        fields = ['ip_address', 'hostname', 'role']


class RestartServiceForm(forms.Form):
    service_name = forms.CharField(
        max_length=100,
        help_text='e.g. kubelet, cri, etcd',
        widget=forms.TextInput(attrs={'placeholder': 'kubelet'}),
    )


class MachineConfigForm(forms.Form):
    MODE_CHOICES = [
        ('auto', 'Auto'),
        ('interactive', 'Interactive'),
        ('reboot', 'Reboot'),
        ('no-reboot', 'No Reboot'),
        ('staged', 'Staged'),
    ]

    yaml_content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 30,
            'class': 'font-monospace',
            'placeholder': 'Machine configuration YAML...',
        }),
    )
    mode = forms.ChoiceField(
        choices=MODE_CHOICES,
        initial='auto',
        help_text='Config apply mode: auto detects if reboot is needed.',
    )

    def clean_yaml_content(self):
        content = self.cleaned_data.get('yaml_content', '')
        content = content.replace('\r\n', '\n').replace('\r', '\n').strip()
        if not content:
            raise forms.ValidationError('Configuration content cannot be empty.')
        try:
            list(yaml.safe_load_all(content))
        except yaml.YAMLError as e:
            raise forms.ValidationError(f'Invalid YAML: {e}')
        return content


class ClusterBootstrapForm(forms.Form):
    cluster_name = forms.CharField(
        max_length=200,
        help_text='Name for the new cluster.',
        widget=forms.TextInput(attrs={'placeholder': 'my-cluster'}),
    )
    endpoint = forms.CharField(
        max_length=500,
        help_text='Cluster endpoint URL (e.g. https://192.168.1.10:6443).',
        widget=forms.TextInput(attrs={'placeholder': 'https://192.168.1.10:6443'}),
    )
    controlplane_ips = forms.CharField(
        help_text='Comma-separated control plane node IPs.',
        widget=forms.TextInput(attrs={'placeholder': '192.168.1.10, 192.168.1.11'}),
    )
    worker_ips = forms.CharField(
        required=False,
        help_text='Comma-separated worker node IPs (optional).',
        widget=forms.TextInput(attrs={'placeholder': '192.168.1.20, 192.168.1.21'}),
    )

    def clean_endpoint(self):
        endpoint = self.cleaned_data.get('endpoint', '').strip()
        if not endpoint.startswith('https://') and not endpoint.startswith('http://'):
            endpoint = 'https://' + endpoint
        return endpoint

    def _parse_ips(self, raw):
        ips = []
        for part in raw.split(','):
            part = part.strip()
            if not part:
                continue
            try:
                ipaddress.ip_address(part)
            except ValueError:
                raise forms.ValidationError(f'"{part}" is not a valid IP address.')
            ips.append(part)
        return ips

    def clean_controlplane_ips(self):
        raw = self.cleaned_data.get('controlplane_ips', '')
        ips = self._parse_ips(raw)
        if not ips:
            raise forms.ValidationError('At least one control plane IP is required.')
        return ips

    def clean_worker_ips(self):
        raw = self.cleaned_data.get('worker_ips', '')
        if not raw.strip():
            return []
        return self._parse_ips(raw)


class NodeApplyConfigForm(forms.Form):
    CONFIG_TYPE_CHOICES = [
        ('custom', 'Upload/paste custom config'),
    ]

    config_content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 20,
            'class': 'font-monospace',
            'placeholder': 'Paste node configuration YAML here...',
        }),
        help_text='YAML configuration to apply to the node.',
    )
    insecure = forms.BooleanField(
        required=False,
        initial=True,
        help_text='Use --insecure flag (required for initial node setup before PKI is established).',
    )

    def clean_config_content(self):
        content = self.cleaned_data.get('config_content', '')
        content = content.replace('\r\n', '\n').replace('\r', '\n').strip()
        if not content:
            raise forms.ValidationError('Configuration content cannot be empty.')
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise forms.ValidationError(f'Invalid YAML: {e}')
        return content
