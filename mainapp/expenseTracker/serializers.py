from rest_framework import serializers
from .models import Expense

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['id', 'title', 'price', 'category', 'date', 'note']
        read_only_fields = ['id']
    
    def validate_price(self, value):
        """Validate price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero")
        return value
    
    def validate_category(self, value):
        """Validate category is one of the allowed choices"""
        allowed_categories = ['Food', 'Transportation', 'Entertainment', 'Shopping', 'Bills', 'Other']
        if value not in allowed_categories:
            raise serializers.ValidationError(f"Category must be one of: {', '.join(allowed_categories)}")
        return value
    
    def to_representation(self, instance):
        """Customize the output representation"""
        representation = super().to_representation(instance)
        # Format price to 2 decimal places
        representation['price'] = '{:.2f}'.format(float(representation['price']))
        # Format date to readable string
        representation['date'] = instance.date.strftime('%Y-%m-%d')
        return representation