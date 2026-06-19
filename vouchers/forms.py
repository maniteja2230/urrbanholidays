"""
Vouchers app forms
"""

from django import forms
from .models import Redemption
from packages.models import TravelPackage


class RedemptionForm(forms.ModelForm):
    """Voucher redemption request form"""
    package = forms.ModelChoiceField(
        queryset=TravelPackage.objects.filter(is_active=True),
        required=False,
        empty_label='Select a package (optional)',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    travel_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    number_of_persons = forms.IntegerField(
        min_value=1, max_value=10,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10})
    )
    special_requests = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Any special requests or requirements...'
        })
    )

    class Meta:
        model = Redemption
        fields = ['package', 'travel_date', 'number_of_persons', 'special_requests']
