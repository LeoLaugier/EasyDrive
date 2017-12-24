from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(label="login", max_length=16)
    password = forms.CharField(label="password", widget=forms.PasswordInput)

class PaginationForm(forms.Form):
	page =forms.IntegerField(label="page")