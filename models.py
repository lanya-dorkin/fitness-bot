from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pydantic import BaseModel

class UserProfile(BaseModel):
    user_id: int
    weight: Optional[float] = None
    height: Optional[float] = None
    age: Optional[int] = None
    activity_minutes: Optional[int] = None
    city: Optional[str] = None
    custom_calorie_goal: Optional[int] = None
    last_update: datetime = datetime.now()
    
    def calculate_water_norm(self, temperature: float) -> float:
        if not self.weight:
            return 0
        
        base_norm = self.weight * 30  # 30ml per kg
        activity_addition = (self.activity_minutes or 0) // 30 * 500  # 500ml per 30min
        temp_addition = 500 if temperature > 25 else 0
        
        return base_norm + activity_addition + temp_addition

    def calculate_calorie_norm(self) -> float:
        if not all([self.weight, self.height, self.age]):
            return 0
        
        if self.custom_calorie_goal:
            return self.custom_calorie_goal
            
        # Basic Harris-Benedict formula
        bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age
        
        # Activity factor
        activity_calories = (self.activity_minutes or 0) * 7  # ~7 calories per minute of activity
        
        return bmr + activity_calories

    def calculate_bmr_per_minute(self) -> float:
        if not all([self.weight, self.height, self.age]):
            return 0
        
        daily_bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age
        return daily_bmr / 1440  # Convert daily BMR to per minute

class FoodEntry(BaseModel):
    food_name: str
    calories: float
    timestamp: datetime
    explanation: str

class WorkoutEntry(BaseModel):
    workout_type: str
    minutes: float
    calories: float
    timestamp: datetime
    explanation: str

class DailyLog(BaseModel):
    date: datetime
    water_intake: float = 0  # in ml
    calorie_intake: float = 0
    calorie_burned_exercise: float = 0
    calorie_burned_bmr: float = 0
    food_log: List[FoodEntry] = []
    workout_log: List[WorkoutEntry] = []
    last_update: datetime = datetime.now()
    
    def update_bmr_calories(self, user: UserProfile):
        now = datetime.now()
        minutes_passed = (now - self.last_update).total_seconds() / 60
        self.calorie_burned_bmr += user.calculate_bmr_per_minute() * minutes_passed
        self.last_update = now

    def calculate_calorie_burned(self) -> float:
        return self.calorie_burned_exercise + self.calorie_burned_bmr

    def calculate_calorie_balance(self) -> float:
        return self.calorie_intake - self.calculate_calorie_burned()

    def calculate_water_balance(self) -> float:
        return self.water_intake - self.calculate_water_norm()

    def calculate_water_norm(self) -> float:
        if not self.weight:
            return 0
        
        base_norm = self.weight * 30  # 30ml per kg
        activity_addition = (self.activity_minutes or 0) // 30 * 500  # 500ml per 30min
        temp_addition = 500 if self.temperature > 25 else 0
        
        return base_norm + activity_addition + temp_addition

    def calculate_calorie_norm(self) -> float:
        if not all([self.weight, self.height, self.age]):
            return 0
        
        if self.custom_calorie_goal:
            return self.custom_calorie_goal
            
        # Basic Harris-Benedict formula
        bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age
        
        # Activity factor
        activity_calories = (self.activity_minutes or 0) * 7  # ~7 calories per minute of activity
        
        return bmr + activity_calories

    def calculate_bmr_per_minute(self) -> float:
        if not all([self.weight, self.height, self.age]):
            return 0
        
        daily_bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age
        return daily_bmr / 1440  # Convert daily BMR to per minute

    def update_bmr_calories(self, user: UserProfile):
        now = datetime.now()
        minutes_passed = (now - self.last_update).total_seconds() / 60
        self.calorie_burned_bmr += user.calculate_bmr_per_minute() * minutes_passed
        self.last_update = now

    def calculate_calorie_burned(self) -> float:
        return self.calorie_burned_exercise + self.calorie_burned_bmr

    def calculate_calorie_balance(self) -> float:
        return self.calorie_intake - self.calculate_calorie_burned()

    def calculate_water_balance(self) -> float:
        return self.water_intake - self.calculate_water_norm()

    def calculate_water_norm(self) -> float:
        if not self.weight:
            return 0
        
        base_norm = self.weight * 30  # 30ml per kg
        activity_addition = (self.activity_minutes or 0) // 30 * 500  # 500ml per 30min
        temp_addition = 500 if self.temperature > 25 else 0
        
        return base_norm + activity_addition + temp_addition

    def calculate_calorie_norm(self) -> float:
        if not all([self.weight, self.height, self.age]):
            return 0
        
        if self.custom_calorie_goal:
            return self.custom_calorie_goal
            
        # Basic Harris-Benedict formula
        bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age
        
        # Activity factor
        activity_calories = (self.activity_minutes or 0) * 7  # ~7 calories per minute of activity
        
        return bmr + activity_calories

    def calculate_bmr_per_minute(self) -> float:
        if not all([self.weight, self.height, self.age]):
            return 0
        
        daily_bmr = 10 * self.weight + 6.25 * self.height - 5 * self.age
        return daily_bmr / 1440  # Convert daily BMR to per minute

    def update_bmr_calories(self, user: UserProfile):
        now = datetime.now()
        minutes_passed = (now - self.last_update).total_seconds() / 60
        self.calorie_burned_bmr += user.calculate_bmr_per_minute() * minutes_passed
        self.last_update = now

    def calculate_calorie_burned(self) -> float:
        return self.calorie_burned_exercise + self.calorie_burned_bmr

    def calculate_calorie_balance(self) -> float:
        return self.calorie_intake - self.calculate_calorie_burned()

    def calculate_water_balance(self) -> float:
        return self.water_intake - self.calculate_water_norm() 