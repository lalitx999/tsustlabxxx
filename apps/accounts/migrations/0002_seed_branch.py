from django.db import migrations


def seed(apps, schema_editor):
    Branch = apps.get_model('accounts', 'Branch')
    if not Branch.objects.exists():
        Branch.objects.create(name='BKK - Siam Square One', address='Siam Square One, Bangkok', is_active=True)


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
