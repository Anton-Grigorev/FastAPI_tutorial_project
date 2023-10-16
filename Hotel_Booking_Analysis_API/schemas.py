from enum import Enum
from pydantic import BaseModel


# URL_1 create class for the expected response format and validate it:
class BookingAllResponse(BaseModel):
    booking_date: str
    id: int
    length_of_stay: int
    daily_rate: float
    guest_name: str


# URL_2 create class for the expected response format and validate it:
class BookingIdResponse(BaseModel):
    booking_date: str
    id: int
    length_of_stay: int
    daily_rate: float
    guest_name: str


# URL_4 define Pydantic models for request and response:
class StatsResponse(BaseModel):
    total_bookigs: int
    average_length_of_stay: float
    average_daily_rate: float


# URL_5 define Pydantic models for request and response:
class Choice(str, Enum):
    booking_trends_by_month = "booking_trends_by_month"
    guest_demographics = "guest_demographics"
    popular_meal_packages = "popular_meal_packages"


class AnalysisRequest(BaseModel):
    analysis_type: Choice


class AnalysisResponse(BaseModel):
    result: dict


# URL_7 create class for the expected response format and validate it
class PopularMealPackage(BaseModel):
    popular_meal_package: str


# URL_8 create class for the expected response format and validate it
class AvgLengthOfStay(BaseModel):
    hotel: str
    arrival_date_year: int
    average_stay: float


# URL_9 create class for the expected response format and validate it
class TotalRevenue(BaseModel):
    hotel: str
    month: str
    total_revenue: float


# URL_10 create class for the expected response format and validate it
class TopCountries(BaseModel):
    country: str
    number_of_bookings: int


# URL_11 create class for the expected response format and validate it
class RepeatedGuestsPercentage(BaseModel):
    percentage_repeated_guests: float


# URL_12 create class for the expected response format and validate it
class TotalGuestsByYearResponse(BaseModel):
    year: int
    total_guests: int


# URL_13 create class for the expected response format and validate it
class AvgDailyRateResort(BaseModel):
    arrival_date_month: str
    average_daily_rate: float


# URL_14 create class for the expected response format and validate it
class MostCommonArrivalDayCity(BaseModel):
    most_common_day: str


# URL_15 create class for the expected response format and validate it
class CountByHotelMeal(BaseModel):
    hotel: str
    meal: str
    count: int


# URL_16 create class for the expected response format and validate it
class TotalRevenueResortByCountry(BaseModel):
    country: str
    total_revenue: float


# URL_17 create class for the expected response format and validate it
class CountByHotelRepeatedGuestResponse(BaseModel):
    hotel: str
    is_repeated_guest: int
    count: int
