from django import forms
from models import MemberProfile

from django.forms.formsets import formset_factory

class MemberSearchForm(forms.Form):
    surname=forms.CharField(max_length=50)

class PersonalEditForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ['dob','home_phone','mobile_phone','address','postcode',
            'veggie','alergies','next_of_kin_name','next_of_kin_relation',
            'next_of_kin_phone']

    def __init__(self, *args, **kwargs):
        super(PersonalEditForm, self).__init__(*args, **kwargs)
        # Make all fields required, then take of the ones that are alright not to
        for field in self.fields:
            self.fields[field].required=True
        self.fields['veggie'].required=False
        self.fields['alergies'].required=False

class MemberEditForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ['dob','home_phone','mobile_phone','address','postcode',
            'veggie','alergies','next_of_kin_name','next_of_kin_relation',
            'next_of_kin_phone','training_for','instructor_number',
            'student_id','associate_id','associate_expiry', 'club_id',
            'club_expiry','club_membership_type','bsac_id','bsac_expiry',
            'bsac_direct_member','bsac_member_via_another_club',
            'bsac_direct_debit','medical_form_expiry','other_qualifications']

class FormExpiryForm(forms.Form):
    user_id=forms.IntegerField()
    user_id.widget=forms.HiddenInput()
    full_name=''
    club_expiry = forms.DateField(input_formats=['%d/%m/%Y'], required=False)
    bsac_expiry = forms.DateField(input_formats=['%d/%m/%Y'], required=False)
    medical_form_expiry = forms.DateField(input_formats=['%d/%m/%Y'], required=False)

FormExpiryFormSet = formset_factory(FormExpiryForm)
