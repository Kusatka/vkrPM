from rest_framework import routers, serializers, viewsets

from .models import Movie, Session


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ["id", "title", "original_title", "year"]


class SessionSerializer(serializers.ModelSerializer):
    movie = serializers.StringRelatedField()
    cinema = serializers.StringRelatedField()
    latest_price_min = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            "id",
            "movie",
            "cinema",
            "starts_at",
            "format",
            "original_language",
            "latest_price_min",
        ]

    def get_latest_price_min(self, obj):
        price = obj.latest_price
        return price.price_min if price else None


class MovieViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer


class SessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Session.objects.select_related("movie", "cinema")
    serializer_class = SessionSerializer


router = routers.DefaultRouter()
router.register("movies", MovieViewSet)
router.register("sessions", SessionViewSet)
