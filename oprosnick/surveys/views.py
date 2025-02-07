from django.shortcuts import render
from .models import Survey, Question, Option, Response, SurveyParticipant

def survey_list(request):
    surveys = Survey.objects.all()
    return render(request, 'survey_list.html', {'surveys': surveys})

def survey_detail(request, survey_id):
    survey = Survey.objects.get(id=survey_id)
    questions = survey.questions.all()
    return render(request, 'survey_detail.html', {'survey': survey, 'questions': questions})

def question_detail(request, question_id):
    question = Question.objects.get(id=question_id)
    options = question.options.all()
    responses = question.responses.all()
    return render(request, 'question_detail.html', {'question': question, 'options': options, 'responses': responses})