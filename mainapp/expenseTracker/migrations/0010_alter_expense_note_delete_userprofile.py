# Generated by Django 5.1.4 on 2025-02-11 05:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenseTracker', '0009_alter_expense_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='note',
            field=models.TextField(blank=True, default='An Expense', max_length=150),
        ),
        migrations.DeleteModel(
            name='UserProfile',
        ),
    ]
