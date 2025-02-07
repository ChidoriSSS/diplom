from surveys.models import Survey
from surveys.models import User

user = User.objects.get(id=1)
survey = Survey.objects.create(
    title= 'rref',
    description = 'dsa',
    created_at = '' ,
    created_by =  user,
)
