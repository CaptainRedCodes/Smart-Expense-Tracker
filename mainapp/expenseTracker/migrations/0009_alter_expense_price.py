# Generated by Django 5.1.4 on 2024-12-21 10:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenseTracker', '0008_alter_expense_options_expense_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
    ]
