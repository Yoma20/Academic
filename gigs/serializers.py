from rest_framework import serializers
from .models import AcademicCategory, Gig, GigPackage, GigExtra, Order, OrderRequirements, Review


class AcademicCategorySerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = AcademicCategory
        fields = ['id', 'name', 'parent', 'subcategories']

    def get_subcategories(self, obj):
        return AcademicCategorySerializer(
            obj.subcategories.all(), many=True
        ).data


class GigPackageSerializer(serializers.ModelSerializer):
    # Allow empty strings from the frontend to be treated as 0/null
    price = serializers.DecimalField(
        max_digits=8, decimal_places=2, coerce_to_string=False
    )
    delivery_days = serializers.IntegerField()
    revision_number = serializers.IntegerField(required=False, default=1)
    features = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    class Meta:
        model = GigPackage
        fields = [
            'id', 'tier', 'name', 'description',
            'price', 'delivery_days', 'revision_number', 'features'
        ]


class GigExtraSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(
        max_digits=8, decimal_places=2, coerce_to_string=False
    )
    extra_days = serializers.IntegerField(required=False, default=0)
    description = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = GigExtra
        fields = ['id', 'name', 'description', 'price', 'extra_days']


class GigSerializer(serializers.ModelSerializer):
    packages = GigPackageSerializer(many=True, read_only=True)
    extras = GigExtraSerializer(many=True, read_only=True)
    expert_username = serializers.CharField(
        source='expert.user.username', read_only=True
    )
    expert_rating = serializers.DecimalField(
        source='expert.rating', max_digits=3,
        decimal_places=2, read_only=True
    )
    expert_id = serializers.IntegerField(source='expert.id', read_only=True)
    starting_price = serializers.ReadOnlyField()
    category_name = serializers.CharField(
        source='category.name', read_only=True, allow_null=True
    )

    class Meta:
        model = Gig
        fields = [
            'id', 'title', 'description', 'short_title', 'short_description',
            'category', 'category_name', 'cover_image', 'images',
            'requirements_prompt', 'sales', 'is_active',
            'expert_id', 'expert_username', 'expert_rating',
            'starting_price', 'packages', 'extras',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['expert', 'sales', 'expert_id', 'expert_username', 'expert_rating']


class GigWriteSerializer(serializers.ModelSerializer):
    """Used for create/update — accepts nested packages and extras."""
    packages = GigPackageSerializer(many=True)
    extras = GigExtraSerializer(many=True, required=False)

    class Meta:
        model = Gig
        fields = [
            'title', 'description', 'short_title', 'short_description',
            'category', 'cover_image', 'images', 'requirements_prompt',
            'packages', 'extras',
        ]

    def create(self, validated_data):
        packages_data = validated_data.pop('packages')
        extras_data = validated_data.pop('extras', [])
        gig = Gig.objects.create(**validated_data)
        for pkg in packages_data:
            GigPackage.objects.create(gig=gig, **pkg)
        for extra in extras_data:
            GigExtra.objects.create(gig=gig, **extra)
        return gig

    def update(self, instance, validated_data):
        packages_data = validated_data.pop('packages', None)
        extras_data = validated_data.pop('extras', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if packages_data is not None:
            instance.packages.all().delete()
            for pkg in packages_data:
                GigPackage.objects.create(gig=instance, **pkg)
        if extras_data is not None:
            instance.extras.all().delete()
            for extra in extras_data:
                GigExtra.objects.create(gig=instance, **extra)
        return instance


class OrderRequirementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderRequirements
        fields = [
            'id', 'citation_style', 'word_count',
            'rubric_file', 'additional_notes', 'answers', 'submitted_at'
        ]
        read_only_fields = ['submitted_at']


class OrderSerializer(serializers.ModelSerializer):
    package = GigPackageSerializer(read_only=True)
    extras = GigExtraSerializer(many=True, read_only=True)
    requirements = OrderRequirementsSerializer(read_only=True)
    student_username = serializers.CharField(
        source='student.username', read_only=True
    )
    gig_title = serializers.CharField(
        source='package.gig.title', read_only=True
    )
    gig_cover = serializers.CharField(
        source='package.gig.cover_image', read_only=True
    )
    expert_username = serializers.CharField(
        source='package.gig.expert.user.username', read_only=True
    )
    requirements_submitted = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'student_username', 'gig_title', 'gig_cover',
            'expert_username', 'package', 'extras',
            'status', 'payment_status',
            'package_price', 'extras_price', 'total_price',
            'deadline', 'requirements', 'requirements_submitted',
            'stripe_payment_intent_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'student', 'package_price', 'extras_price', 'total_price',
            'payment_status', 'stripe_payment_intent_id',
        ]

    def get_requirements_submitted(self, obj):
        return hasattr(obj, 'requirements')
    
class ReviewSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    expert_username = serializers.CharField(source='expert.user.username', read_only=True)
    order_gig_title = serializers.CharField(source='order.package.gig.title', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'order', 'expert', 'student',
            'student_username', 'expert_username', 'order_gig_title',
            'rubric_adherence_score', 'timeliness_score', 'communication_score',
            'rating', 'comment', 'would_recommend', 'created_at',
        ]
        read_only_fields = ['student', 'expert', 'rating']