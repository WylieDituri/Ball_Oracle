from django.db import models

class Game (models.Model):
    home_team = models.CharField(max_length=3)
    home_code = models.IntegerField()
    away_team = models.CharField(max_length=3)
    away_code = models.IntegerField()
    home_score = models.IntegerField()
    away_score = models.IntegerField()
    game_date = models.DateField()
    home_predicted_score = models.IntegerField()
    away_predicted_score = models.IntegerField()
