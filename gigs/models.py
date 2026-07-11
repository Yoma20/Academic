from django.db import models
from django.conf import settings
from django.utils.text import slugify
from expert_profiles.models import ExpertProfile
from django.core.validators import MinValueValidator, MaxValueValidator


class AcademicCategory(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='subcategories'
    )

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Academic Categories'

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Gig(models.Model):
    expert = models.ForeignKey(
        ExpertProfile,
        on_delete=models.CASCADE,
        related_name='gigs'
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    short_title = models.CharField(max_length=100)
    short_description = models.CharField(max_length=255)
    category = models.ForeignKey(
        AcademicCategory,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='gigs'
    )
    cover_image = models.URLField(blank=True)
    images = models.JSONField(default=list, blank=True)

    requirements_prompt = models.TextField(
        blank=True,
        help_text="Questions the student must answer before work begins "
                  "(e.g. citation style, word count, rubric upload)."
    )

    sales = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_pinned = models.BooleanField(
        default=False,
        help_text="Admin-pinned gigs are surfaced at the top of listings."
    )
    pinned_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When this gig was pinned. Cleared when unpinned."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            # Ensure uniqueness
            while Gig.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def starting_price(self):
        pkg = self.packages.order_by('price').first()
        return pkg.price if pkg else None


class GigPackage(models.Model):
    TIER_CHOICES = (
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    )
    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name='packages')
    tier = models.CharField(max_length=10, choices=TIER_CHOICES)
    name = models.CharField(max_length=100, help_text="e.g. 'Literature Review'")
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_days = models.PositiveSmallIntegerField()
    revision_number = models.PositiveSmallIntegerField(default=1)
    features = models.JSONField(default=list, help_text="List of included features")

    class Meta:
        unique_together = ('gig', 'tier')
        ordering = ['price']

    def __str__(self):
        return f"{self.gig.title} — {self.get_tier_display()}"


class GigExtra(models.Model):
    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name='extras')
    name = models.CharField(max_length=100, help_text="e.g. '24-hour turnaround'")
    description = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    extra_days = models.PositiveSmallIntegerField(
        default=0,
        help_text="Additional delivery days this extra adds."
    )

    def __str__(self):
        return f"{self.gig.title} — Extra: {self.name}"


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('held', 'Held'),
        ('released', 'Released'),
        ('refunded', 'Refunded'),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    package = models.ForeignKey(
        GigPackage,
        on_delete=models.PROTECT,
        related_name='orders',
        null=True,
        blank=True,
    )
    extras = models.ManyToManyField(GigExtra, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid'
    )

    package_price = models.DecimalField(max_digits=10, decimal_places=2)
    extras_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    deadline = models.DateTimeField(null=True, blank=True)



    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.student.username}"


class OrderRequirements(models.Model):
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='requirements'
    )
    citation_style = models.CharField(
        max_length=20,
        choices=(
            ('APA', 'APA'), ('MLA', 'MLA'),
            ('Chicago', 'Chicago'), ('Harvard', 'Harvard'), ('Other', 'Other'),
        ),
        blank=True
    )
    word_count = models.PositiveIntegerField(null=True, blank=True)
    rubric_file = models.FileField(
        upload_to='orders/rubrics/', null=True, blank=True
    )
    additional_notes = models.TextField(blank=True)
    answers = models.JSONField(
        default=dict, blank=True,
        help_text="Free-form answers to the gig's requirements_prompt questions."
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Requirements for Order #{self.order.id}"


class Review(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='review',
    )
    expert = models.ForeignKey(
        ExpertProfile,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_given',
    )
    rubric_adherence_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    timeliness_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    communication_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    comment = models.TextField(blank=True)
    would_recommend = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_rating(self):
        return round(
            (self.rubric_adherence_score * 0.50) +
            (self.timeliness_score * 0.25) +
            (self.communication_score * 0.25),
            2
        )

    def save(self, *args, **kwargs):
        self.rating = self.calculate_rating()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Review for Order #{self.order.id} — {self.rating}/5"