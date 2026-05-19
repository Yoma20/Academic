from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0003_conversation_gig_message_message_type_offer_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='messaging/attachments/'),
        ),
        migrations.AddField(
            model_name='message',
            name='file_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='message',
            name='content',
            field=models.TextField(blank=True, max_length=5000),
        ),
        migrations.AlterField(
            model_name='message',
            name='message_type',
            field=models.CharField(
                choices=[('text', 'Text'), ('offer', 'Offer'), ('file', 'File')],
                default='text',
                max_length=10,
            ),
        ),
    ]