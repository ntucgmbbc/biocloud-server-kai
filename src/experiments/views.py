import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.html import mark_safe
from django.utils.translation import ugettext
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView

from core.decorators import ajax_required
from data_sources.models import DataSource
from .forms import ExperimentCreateForm
from .models import Experiment, Condition


@require_POST
@ajax_required
@login_required
def get_experiment_info_json(request):
    def condition_as_dict(condition):
        """Condition JSON formatter"""
        return {
            'file_path': condition.data_source.file_path,
            # 'strand': condition.strand,
            # 'file_type': condition.data_source.file_type,
        }

    try:
        pk = request.POST['experiment_pk']
    except KeyError:
        return HttpResponseBadRequest
    experiment = get_object_or_404(
        Experiment,
        owner=request.user,
        pk=pk
    )
    return JsonResponse({
        'name': experiment.name,
        'url': experiment.get_absolute_url(),
        'conditions': list(experiment.condition_names),
        'conditionSampleGroups': [
            {
                "condition": cond_label._asdict(),
                "samples": [
                    {
                        "name": name,
                        "conditions": [
                            condition_as_dict(cond) for cond in conditions
                        ]
                    }
                    for name, conditions in samples.items()
                ]
            }
            for cond_label, samples in experiment.group_data_sources.items()
        ],
    })


@login_required
def create_new_experiment(request):
    if request.method == 'POST':
        form = ExperimentCreateForm(
            data=request.POST, files=request.FILES,
        )
        extra_data = json.loads(request.POST.get('extraData', {}))
        conditions = extra_data.get('conditions', [])
        condition_labels = {
            cond['_uid']: cond['label']
            for cond in conditions
        }
        num_condition_created = max(
            extra_data.get('numConditionCreated', 0),
            len(conditions)
        )
        labelled_data_sources = extra_data.get('dataSources', [])
        if form.is_valid():
            # Create the experiment first
            experiment = form.save(commit=False)
            experiment.owner = request.user
            experiment.save()
            # Create all conditions of the experiment
            condition_objects = [
                Condition(
                    experiment=experiment,
                    condition=condition_labels[ds['condition']],
                    condition_order=ds['condition'],
                    data_source=DataSource.objects.get(
                        pk=ds['data_source_pk']
                    ),
                    sample_name=ds['sample'],
                    strand=ds['metadata'].get('strand', ''),
                )
                for ds in labelled_data_sources if ds['selected']
            ]
            Condition.objects.bulk_create(condition_objects)
            messages.success(request, ugettext(
                'You have created a new experiment {name}'.format(
                    name=experiment.name
                ),
            ))
            return redirect('index')
        # if the form is invalid, remain this form instance and pass to the
        # render() at the end (all errors has been generated during the
        # form.is_valid() check.
    else:
        form = ExperimentCreateForm()
        # get user's sample with metadata
        data_sources = request.user.data_sources.all()
        labelled_data_sources = [
            {
                'data_source_pk': ds.pk,
                'file_path': ds.file_path,
                'file_type': ds.file_type,
                'sample': ds.sample_name,
                'metadata': ds.metadata,
                'condition': 0,
                'selected': False,
            }
            for ds in data_sources
        ]
        conditions = []
        num_condition_created = len(conditions)
    return render(request, 'experiments/new.html', {
        'form': form,
        'data_source_json': mark_safe(json.dumps(labelled_data_sources)),
        'conditions_json': mark_safe(json.dumps(conditions)),
        'num_condition_created': num_condition_created,
    })


class ExperimentListView(LoginRequiredMixin, ListView):
    model = Experiment
    template_name = "experiments/list.html"

    def get_queryset(self):
        return self.request.user.experiments.all()
        # return super().get_queryset().filter(
        #     owner__exact=self.request.user,
        # )


class ExperimentDetailView(LoginRequiredMixin, DetailView):
    model = Experiment
    template_name = "experiments/detail.html"

    def get_queryset(self):
        return self.request.user.experiments.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['experiment'] = context['object']
        return context
