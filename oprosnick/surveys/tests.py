from surveys.models import Survey
from surveys.models import User
from surveys.models import Question

user = User.objects.get(id=1)
survey = Survey.objects.create(
    title= 'rref',
    description = 'dsa',
    created_at = '' ,
    created_by =  user,
)

sur = Survey.objects.get(id=1)
print(sur.id)
question = Question.objects.create(
    question_text = 'Кнопка',
    question_type = 'Красный',
    survey_id = sur.id
)