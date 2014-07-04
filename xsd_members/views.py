from django.contrib.auth.models import User

from django.views.generic.base import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView, DeleteView

from django.forms.formsets import formset_factory

from django.db.models import Q

from django.template import RequestContext
from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse, reverse_lazy

from xsd_members.models import MemberProfile
from xsd_members.forms import *

from xsd_frontend.models import UpdateRequest
from xsd_frontend.forms import UpdateRequestReply

from xSACdb.view_helpers import OrderedListView
from xSACdb.roles.decorators import require_members_officer
from xSACdb.roles.mixins import RequireMembersOfficer

import datetime
import StringIO
import csv

def view_my_profile(request):
    profile=request.user.get_profile
    editable=True
    return render(request,'members_detail.html',{
        'member':profile,
        'editable':editable,
        'myself':True},
        context_instance=RequestContext(request))

def admin(request):
    return redirect(reverse('MemberSearch'))

class MemberSearch(RequireMembersOfficer, OrderedListView):
    model=MemberProfile
    template_name='members_search.html'
    context_object_name='members'
    order_by='user__last_name'

    def get_queryset(self):
        if 'surname' in self.request.GET:
            surname=self.request.GET['surname']
            queryset=super(MemberSearch, self).get_queryset()
            queryset=queryset.filter(user__last_name__contains=surname)
        else:
            queryset=None
        return queryset

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(MemberSearch, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['search_form'] = MemberSearchForm()
        return context

class MemberList(RequireMembersOfficer, OrderedListView):
    model=MemberProfile
    template_name='members_list.html'
    context_object_name='members'
    order_by='user__last_name'
    page_title='Club Membership Listing'
    page_description='Our entire membership (that has registered for the database)'

    def get_context_data(self, **kwargs):
        context = super(MemberList, self).get_context_data(**kwargs)
        context['page_title'] = self.page_title
        context['page_description'] = self.page_description
        return context

class NewMembers(MemberList):
    page_title='New Members'
    page_description='New signups to the database, to remove them from this list use <div class="fake-button"><i class="icon-flag"></i> Remove New Flag</div> on their profile page'

    def get_queryset(self):
        queryset=super(NewMembers, self).get_queryset()
        queryset=queryset.filter(new_notify=True)
        return queryset

class MembersExpiredFormsList(MemberList):
    page_title='Members With Expired Forms'
    page_description='''<p><i class="icon-bsac-small expired"></i>is expired 
        BSAC membership, <i class="icon-home expired"></i>is expired club 
        membership and <i class="icon-medkit expired"></i>is an expired
        medical form.</p>
        <p>The easiest way of bulk adding forms is the Bulk Jobs > Add Forms
        Tool.</p>'''

    def get_queryset(self):
        queryset=super(MembersExpiredFormsList, self).get_queryset()
        today=datetime.date.today()
        queryset=queryset.filter(Q(bsac_expiry__lte=today) | Q (bsac_expiry=None) | \
            Q(club_expiry__lte=today) | Q(club_expiry=today) | \
            Q(medical_form_expiry__lte=today) | Q(medical_form_expiry=None))
        return queryset

class MembersMissingFieldsList(MemberList):
    page_title='Members With Missing Personal Fields'
    page_description='''<p>The only reason a member will be on this list is
        that they failed to fill out the form shown to them when they signed up
        to the database. This form will be shown to them when they log in
        again, they will not be able to use other parts of the database until
        this form is completed.'''

    blank_fields=['address','postcode','home_phone','mobile_phone','next_of_kin_name','next_of_kin_relation','next_of_kin_phone']

    def build_queryset(self):
        qObj = None
        for field in self.blank_fields:
            newQ = Q(**{field :  ''}) 
            if qObj is None:
                qObj = newQ
            else:
                qObj = qObj | newQ
        return qObj

    def get_queryset(self):
        queryset=super(MembersMissingFieldsList, self).get_queryset()
        queryset_filtered=queryset.filter(self.build_queryset())
        return queryset_filtered

class MemberDetail(RequireMembersOfficer, DetailView):
    model=MemberProfile
    template_name='members_detail.html'
    context_object_name='member'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(MemberDetail, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['editable']        = True
        return context
    def get_object(self):
        user_pk=self.kwargs['user__pk']
        user=User.objects.get(pk=user_pk)
        return user.get_profile()

    def get(self, request, *args, **kwargs):
        if 'action' in request.GET:
            action=request.GET['action']
            if action=='remove-new-flag':
                p=self.get_object()
                p.new_notify=False
                p.save()

        return super(MemberDetail, self).get(request, *args, **kwargs)

class ModelFormView(FormView):
    def get_model(self):
        pass

    def get_initial(self):
        initial={}
        model=self.get_model()
        for field in self.form_class._meta.fields:
            initial[field]=getattr(model,field)
        return initial
    def form_valid(self, form):
        model=self.get_model()
        for field in form.cleaned_data:
            setattr(model, field, form.cleaned_data[field])
        model.save()
        return super(ModelFormView, self).form_valid(form)

class MyProfileEdit(ModelFormView):
    template_name='members_edit.html'
    form_class=MemberEditForm
    success_url=reverse_lazy('my-profile')

    def get_model(self):
        return self.request.user.get_profile()

    def get_context_data(self, **kwargs):
        context = super(MyProfileEdit, self).get_context_data(**kwargs)
        context['member'] = self.get_model()
        return context

class MemberEdit(RequireMembersOfficer, ModelFormView):
    template_name='members_edit.html'
    form_class=MemberEditForm

    def get_user(self):
        pk=self.kwargs['pk']
        user=get_object_or_404(User,pk=pk)
        return user

    def get_success_url(self):
        user = self.get_user()
        return reverse('MemberDetail', kwargs={'user__pk':user.pk})

    def get_model(self):
        user=self.get_user()
        return user.get_profile()

    def get_context_data(self, **kwargs):
        context = super(MemberEdit, self).get_context_data(**kwargs)
        context['member'] = self.get_model()
        return context

class MemberDelete(RequireMembersOfficer, DeleteView):
    model=User
    template_name='members_delete.html'
    success_url = reverse_lazy('MembersList')
    context_object_name='u'

    # def get_context_data(self, **kwargs):
    #     context = super(SessionDelete, self).get_context_data(**kwargs)
    #     context['pls'] = PerformedLesson.objects.filter(session=self.object)
    #     return context

@require_members_officer
def select_tool(request):
    return render(request,'members_bulk_select.html',{
        },
        context_instance=RequestContext(request))

class BulkAddForms(RequireMembersOfficer, View):
    model=MemberProfile
    

    def get(self, request, *args, **kwargs):
        spreadsheet=False
        if 'set' in request.GET:
            if request.GET['set']=='all':
                members=self.get_all_objects()
            spreadsheet=True
        elif 'names' in request.GET and request.GET['names']!='':
            from bulk_select import get_bulk_members
            members=get_bulk_members(request)
            spreadsheet=True
        if spreadsheet:
            FormExpiryFormSet = formset_factory(FormExpiryForm, extra=0)
            initial=[]
            for member in members:
                initial.append({'user_id':member.user.pk})
            formset=FormExpiryFormSet(initial=initial)
            for member,form in zip(members,formset):
                form.full_name=member.user.get_full_name()

            return render(request,'members_bulk_edit_forms.html',{
                'page_title':'Bulk Select Results',
                'formset':formset,
            },
            context_instance=RequestContext(request))
        else:
            # First form
            return render(request,'members_bulk_select.html',{
            },
            context_instance=RequestContext(request))

    def get_all_objects(self):
        return self.model.objects.all()

    def post(self, request, *args, **kwargs):
        formset=FormExpiryFormSet(request.POST)
        if formset.is_valid():
            for form in formset.cleaned_data:
                mp=MemberProfile.objects.get(user__pk=form['user_id'])
                if form['club_expiry']: mp.club_expiry=form['club_expiry']
                if form['bsac_expiry']: mp.bsac_expiry=form['bsac_expiry']
                if form['medical_form_expiry']: mp.medical_form_expiry=form['medical_form_expiry']
                mp.save()
        else:
            print "UNCLEAN!"

        return redirect(reverse('BulkAddForms'))

from xsd_frontend.base import BaseUpdateRequestList, BaseUpdateRequestRespond

class MemberUpdateRequestList(RequireMembersOfficer, BaseUpdateRequestList):
    template_name="members_update_request.html"
    area='mem'
    form_action=reverse_lazy('MemberUpdateRequestRespond')
    custom_include='members_update_request_custom.html'

class MemberUpdateRequestRespond(RequireMembersOfficer, BaseUpdateRequestRespond):
    success_url=reverse_lazy('MemberUpdateRequestList')
