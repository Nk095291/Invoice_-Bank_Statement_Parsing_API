from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='content_hash',
            field=models.CharField(db_index=True, max_length=64),
        ),
        migrations.AddConstraint(
            model_name='document',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_deleted', False)),
                fields=('content_hash',),
                name='unique_active_content_hash',
            ),
        ),
    ]
