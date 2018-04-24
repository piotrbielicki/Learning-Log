from __future__ import print_function
from telesign.messaging import MessagingClient

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.template.context_processors import request
from django.views.generic.edit import UpdateView
from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin

from learning_logs.forms import LoginForm
from .forms import TopicForm, EntryForm, EditEntryForm
from .models import Topic, Entry
from django.views import View


def send_sms(message):
    customer_id = ""
    api_key = ""

    phone_number = ""
    message_type = "ARN"

    messaging = MessagingClient(customer_id, api_key)
    response = messaging.message(phone_number, message, message_type)


def index(request):
    return render(request, 'index.html')

class TopicsView(LoginRequiredMixin, View):

    def get(self, request):
        topics = Topic.objects.filter(owner=request.user).order_by('date_added')

        return render(request, 'topics.html',  {'topics': topics})

class TopicView(LoginRequiredMixin, View):

    def get(self, request, topic_id):
        topic = Topic.objects.get(id=topic_id)
        if topic.owner != request.user:
            raise Http404
        entries = topic.entry_set.order_by('-date_added')

        return render(request, 'topic.html',  {'topic': topic,
                                               'entries': entries})

class NewTopicView(View):

    def get(self, request):
        form = TopicForm
        return render(request, 'new_topic.html', {'form': form})

    def post(self, request):
        form = TopicForm(request.POST)
        if form.is_valid():
            new_topic = form.save(commit=False)
            new_topic.owner = request.user
            new_topic.save()
            form.save()
            return HttpResponseRedirect(reverse('topics'))

class NewEntryView(LoginRequiredMixin, View):

    def get(self, request, topic_id):
        topic = Topic.objects.get(id=topic_id)
        form = EntryForm()
        return render(request, 'new_entry.html', {'topic': topic,
                                                  'form': form})

    def post(self, request, topic_id):
        form = EntryForm(request.POST)
        if form.is_valid():
            new_entry = form.save(commit=False)
            topic = Topic.objects.get(id=topic_id)
            if topic.owner != request.user:
                message = 'Aby opublikować post, musisz być włascicielem tego tematu.'
                return render(request, 'new_entry.html', {'topic': topic,
                                                          'form': form,
                                                          'message': message})
            new_entry.topic = topic
            new_entry.save()

            message = 'Użytkownik {}, dodał nowy wpis w temacie "{}" .'.format(request.user, topic.text)
            send_sms(message)

            return HttpResponseRedirect(reverse('topic', args=[topic_id]))


def edit_entry(request, entry_id):
    entry = Entry.objects.get(id=entry_id)
    topic = entry.topic
    if topic.owner != request.user:
        raise Http404
    if request.method != 'POST':
        form = EntryForm(instance=entry)
    else:
        form = EntryForm(instance=entry, data=request.POST)
        if form.is_valid():
            form.save()
            message = 'Użytkownik {}, edytował wpis w temacie "{}" .'.format(request.user, topic.text)
            send_sms(message)
            return HttpResponseRedirect(reverse('topic', args=[topic.id]))

    return render(request, 'edit_entry.html', {'entry': entry,
                                               'topic': topic,
                                               'form': form})

class LoginView(View):

    def get(self, request):
        form = LoginForm()
        return render(request, 'login.html', {'form': form})


    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('/')

            else:
                message = 'Nazwa użytkownika i hasło są nieprawidłowe. Proszę spróbować ponownie.'
                return render(request, 'login.html', {'form': form,
                                                         'message': message})

class LogoutView(View):

    def get(self, request):
        logout(request)

        return redirect('/')

class RegisterView(View):

    def get(self, request):
        form = UserCreationForm()
        return render(request, 'register.html', {'form': form})

    def post(self, request):
        form = UserCreationForm(data=request.POST)
        if form.is_valid():
            new_user = form.save()
            authenticated_user = authenticate(username=new_user.username, password=request.POST['password1'])
            login(request, authenticated_user)
            message = 'Nowy użytkownik w serwisie! {} założył konto.'.format(new_user.username)
            send_sms(message)
            return HttpResponseRedirect(reverse('index'))
