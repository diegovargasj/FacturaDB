from django import forms

from FacturaDB.models import Factura


class SearchForm(forms.Form):
	amount = forms.CharField(required=False,
	                         widget=forms.TextInput(
		                         attrs={'placeholder': 'Monto',
		                                'style': 'border: none'}))
	year = forms.IntegerField(required=False, min_value=0,
	                          widget=forms.TextInput(
		                          attrs={'placeholder': 'Año'}))
	month = forms.IntegerField(widget=forms.Select(choices=(
		('', '--'), ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
		('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'), ('7', 'Julio'),
		('8', 'Agosto'), ('9', 'Septiembre'), ('10', 'Octubre'),
		('11', 'Noviembre'), ('12', 'Diciembre'))), required=False)


class CancelForm(forms.Form):
	cancel = forms.CharField(widget=forms.HiddenInput(
		attrs={'name': 'cancel', 'class': 'cancel'}
	), required=False)
	pk = forms.IntegerField(widget=forms.HiddenInput(
		attrs={'name': 'pk', 'class': 'pk'}), required=False)
	amount = forms.CharField(widget=forms.HiddenInput(
		attrs={'name': 'amount', 'value': '',
		       'class': 'amount'}), required=False)
	year = forms.IntegerField(widget=forms.HiddenInput(
		attrs={'name': 'year', 'class': 'year', 'value': ''}), required=False)
	month = forms.IntegerField(widget=forms.HiddenInput(
		attrs={'name': 'month', 'class': 'month', 'value': ''}), required=False)
	date = forms.DateField(widget=forms.TextInput(
							attrs={'readonly':True})


class SearchAllForm(forms.Form):
	amount = forms.CharField(required=False,
	                         widget=forms.TextInput(
		                         attrs={'placeholder': 'Monto'}))
	client_rut = forms.CharField(required=False, max_length=15,
	                             widget=forms.TextInput(
		                             attrs={'placeholder': 'Rut Cliente'}))
	fnum = forms.CharField(required=False, max_length=20,
	                       widget=forms.TextInput(
		                       attrs={'placeholder': 'N° Factura'}))
	date = forms.DateField(required=False,
	                       widget=forms.TextInput(
		                       attrs={'readonly': True}
	                       ))
	date_cancelled = forms.DateField(required=False,
	                                 widget=forms.TextInput(
		                                 attrs={'readonly': True}
	                                 ))
	paid = forms.CharField(required=False, widget=forms.Select(
		choices=(('', '--'), ('True', 'Si'), ('False', 'No'))))
	CHOICES = (('client__name', 'Nombre'),
	           ('client__rut', 'Rut'), ('num', 'N°'),
	           ('monto', 'Monto'), ('fecha', 'Fecha'))
	order_by = forms.CharField(widget=forms.Select(choices=CHOICES,
	                            attrs={'onchange': 'this.form.submit()'}))
