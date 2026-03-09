class ExpertProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = ExpertProfile
        fields = ['id', 'username', 'email', 'field_of_study', 'bio', 'available', 'rating']
        read_only_fields = ['rating']  # prevent self-rating manipulation
```

---

**6. Add db.sqlite3 to .gitignore**

Create or update `.gitignore` in the repo root:
```
# .gitignore
db.sqlite3
*.pyc
__pycache__/
.env
media/
staticfiles/


