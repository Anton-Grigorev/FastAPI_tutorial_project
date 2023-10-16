from authentication import *
from schemas import *
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query, Security, Path
from fastapi.security import HTTPBasicCredentials

from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.types import TypeDecorator
from sqlalchemy import DateTime

import pandas as pd

import uvicorn

# create bd SQLite
DATABASE_URL = "sqlite:///hotel.db"
db_engine = create_engine(DATABASE_URL)

# defining the schema of the "bookings" table
Base = declarative_base()


# create custom data type for date conversion
class CustomDateTime(TypeDecorator):
    impl = DateTime

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.strftime("%Y-%m-%d")
        return None


# create table
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_date = Column(CustomDateTime)
    length_of_stay = Column(Integer)
    guest_name = Column(String)
    daily_rate = Column(Float)


# create the table in db
Base.metadata.create_all(bind=db_engine)

# create a session to work with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
session = SessionLocal()

# load the dataset into a pandas DataFrame
df = pd.read_csv("hotel_booking_data.csv")

# create, filter DataFrame for the db
df1 = df.copy()
df1["id"] = range(1, len(df1) + 1)
df1["booking_date"] = pd.to_datetime(
    df1["arrival_date_year"].astype(str)
    + "-"
    + df1["arrival_date_month"]
    + "-"
    + df1["arrival_date_day_of_month"].astype(str)
)
df1["length_of_stay"] = df1.stays_in_weekend_nights + df1.stays_in_week_nights
df1["guest_name"] = df1.name
df1["daily_rate"] = df1.adr
df1 = df1[["id", "booking_date", "length_of_stay", "guest_name", "daily_rate"]]

# load df1 in the table
df1.to_sql("bookings", con=db_engine, if_exists="replace", index=False)

# set up the FastAPI application
app = FastAPI(title="Hotel Booking Analysis API")


# dependency function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# URL_1
@app.get(
    "/bookings",
    summary="Get All Bookings",
    response_model=list[BookingAllResponse],
    tags=["Bookings"],
    status_code=200,
)
async def get_all_bookings(
    skip: int = Query(0, description="Skip a number of bookings", ge=0),
    limit: int = Query(
        10, description="Limit the number of bookings to retrieve", ge=0, le=100
    ),
    db: Session = Depends(get_db),
) -> list:
    """
    Retrieves a list of all bookings in the dataset.
    Since the database is very large, and the task is to show all bookings, a restriction on display on the page has been introduced - the 'limit' parameter

    return: list of the dict with data: booking_date, id, length_of_stay, daily_rate, guest_name.

    Expected response format:
    [
     {
       "booking_date": "0000-00-00",
       "id": 0,
       "length_of_stay": 0,
       "daily_rate": 0,
       "guest_name": "string"
      }
    ]


    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """
    bookings = db.query(Booking).offset(skip).limit(limit).all()
    return bookings


# URL_2
@app.get(
    "/bookings/{booking_id}",
    summary="Get item by ID",
    response_model=BookingIdResponse,
    tags=["Bookings"],
    status_code=200,
)
async def get_booking_id(
    booking_id: int = Path(..., description="ID", ge=1), db: Session = Depends(get_db)
) -> dict:
    """
    Retrieves details of a specific booking by its unique ID.

    Parameter:
    booking_id: int

    return: dict with data: booking_date, id, length_of_stay, daily_rate, guest_name.

    Expected response format:
    {
     "booking_date": "0000-00-00",
     "id": 0,
     "length_of_stay": 0,
     "daily_rate": 0,
     "guest_name": "string"
    }



    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 404 Not Found.
    """

    booking = db.query(Booking).get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


# URL_3
@app.get(
    "/bookings/search/",
    summary="Search Bookings",
    tags=["Bookings"],
    status_code=200,
)
async def search_bookings(
    guest_name: str = Query(
        None, description="Guest name", min_length=2, max_length=20
    ),
    booking_date: str = Query(
        None, description="Booking date. Format: y-m-d: 0000-00-00", max_length=10
    ),
    length_of_stay: int = Query(None, description="Length of stay", ge=0),
    db: Session = Depends(get_db),
):
    """
    Allows searching for bookings based on various parameters such as guest name, booking dates, length of stay.

    return: dict with data: booking_date, id, length_of_stay, daily_rate, guest_name.

    Expected response format:
    [
     {
       "booking_date": "0000-00-00",
       "id": 0,
       "length_of_stay": 0,
       "daily_rate": 0,
       "guest_name": "string"
      }
    ]


    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 400 Bad Request: Guest not found or Date not found or Length of stay not found
    """

    query = db.query(Booking)

    if guest_name is not None:
        query = query.filter(Booking.guest_name == guest_name)
        existing_guest = query.first()
        if existing_guest is None:
            raise HTTPException(status_code=400, detail="Guest not found")

    if booking_date:
        date_obj = datetime.strptime(booking_date, "%Y-%m-%d").date()
        query = query.filter(Booking.booking_date == date_obj)
        if not query.first():
            raise HTTPException(status_code=400, detail="Date not found")

    if length_of_stay is not None:
        query = query.filter(Booking.length_of_stay == length_of_stay)
        if not query.first():
            raise HTTPException(status_code=400, detail="Length of stay not found")

    bookings = query.all()
    return bookings


# URL_4
@app.get(
    "/bookings/stats/",
    summary="Get Stats",
    response_model=StatsResponse,
    tags=["Bookings"],
    status_code=200,
)
async def get_stats() -> dict:
    """
    Performs advanced analysis on the dataset, generating insights and trends based on specific criteria, such as booking trends by month, guest demographics, popular meal packages, etc.

    return: dict with data: total_bookigs, average_length_of_stay, average_daily_rate.

    Expected response format:
    {
      "total_bookigs": 0,
      "average_length_of_stay": 0,
      "average_daily_rate": 0
    }


    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """
    try:
        total_bookigs = df.shape[0]
        new_df = df.copy()
        new_df["length_of_stay"] = (
            new_df.stays_in_weekend_nights + new_df.stays_in_week_nights
        )
        average_length_of_stay = new_df.length_of_stay.mean()
        average_daily_rate = new_df.adr.mean()

        return {
            "total_bookigs": total_bookigs,
            "average_length_of_stay": average_length_of_stay,
            "average_daily_rate": average_daily_rate,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_5
@app.get(
    "/bookings/analysis/",
    summary="Advanced Analysis",
    response_model=AnalysisResponse,
    tags=["Bookings"],
)
async def perform_advanced_analysis(
    request_data: Choice = Query(description="Your choice"),
) -> dict:
    """
    Performs advanced analysis on the dataset, generating insights and trends based on specific criteria, such as booking trends by month, guest demographics, popular meal packages, etc.

    Parameter to choose:
    booking_trends_by_month
    guest_demographics
    popular_meal_packages

    return: dict with data.


    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 400 Bad Request.
    """

    result = {}

    if request_data == Choice.booking_trends_by_month:
        # Calculate booking trends by month
        booking_trends = df["arrival_date_month"].value_counts().to_dict()
        result["booking_trends_by_month"] = booking_trends

    elif request_data == Choice.guest_demographics:
        # Calculate guest demographics
        demographics = {
            "total_adults": int(df["adults"].sum()),
            "total_children": int(df["children"].sum()),
            "total_babies": int(df["babies"].sum()),
        }
        result["guest_demographics"] = demographics

    elif request_data == Choice.popular_meal_packages:
        # Calculate popular meal packages
        meal_packages = df["meal"].value_counts().to_dict()
        result["popular_meal_packages"] = meal_packages

    else:
        raise HTTPException(status_code=400, detail="Invalid analysis_type")

    return {"result": result}


# URL_6
@app.get(
    "/bookings/nationality/",
    summary="Get a sample by nationality",
    tags=["Bookings"],
    status_code=200,
)
async def get_nationality(
    nationality: str = Query(
        description="Must not exceed 3 big letters", min_length=2, max_length=3
    )
):
    """
    Retrieves bookings based on the provided nationality.

    Parameters:
    nationality (str): The nationality for which to retrieve bookings. Must not exceed 3 big letters.

    return: The bookings matching the provided nationality.


    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 400 Bad Request.
    - 404 Not Found.
    """

    if len(nationality) > 3:
        raise HTTPException(status_code=400, detail="Must not exceed 3 big letters")
    if nationality not in df.country.unique():
        raise HTTPException(status_code=404, detail="Invalid nationality")

    national = df.query("country == @nationality")

    if len(national) == 0:
        raise HTTPException(
            status_code=404, detail=f"No bookings found for nationality: {nationality}"
        )

    return national.to_json()


# URL_7
@app.get(
    "/bookings/popular_meal_package/",
    summary="Get most popular meal package",
    response_model=PopularMealPackage,
    tags=["Bookings"],
    status_code=200,
)
async def get_popular_meal_package() -> dict:
    """
    Retrieves the most popular meal package among all bookings.

    return: The most popular meal package.

    Expected response format:
    {"popular_meal_package": "string"}

    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """

    try:
        return {"popular_meal_package": df.meal.value_counts().index[0]}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_8
@app.get(
    "/bookings/avg_length_of_stay/",
    summary="Get average length of stay by booking year and hotel type",
    response_model=list[AvgLengthOfStay],
    tags=["Bookings"],
    status_code=200,
)
async def get_avg_length_of_stay() -> list:
    """
     Retrieves the average length of stay grouped by booking year and hotel type.

     return: The average length of stay for each combination of booking year and hotel type.

     Expected response format:
     [
     {
      "hotel": "string",
      "arrival_date_year": 0,
      "average_stay": 0
     }
    ]

     HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
     - 500 Internal Server Error: Internal server error.
    """
    try:
        new_df = df.copy()
        new_df["length_of_stay"] = (
            new_df.stays_in_weekend_nights + new_df.stays_in_week_nights
        )
        return (
            new_df.groupby(["hotel", "arrival_date_year"])["length_of_stay"]
            .mean()
            .reset_index(name="average_stay")
            .to_dict("records")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_9
@app.get(
    "/bookings/total_revenue/",
    summary="Get total revenue by booking month and hotel type",
    response_model=list[TotalRevenue],
    tags=["Bookings"],
    status_code=200,
)
async def get_total_revenue() -> list:
    """
    Retrieves the total revenue grouped by booking month and hotel type.

    return: The total revenue for each combination of booking month and hotel type.

    Expected response format:
    [
     {
      "hotel": "string",
      "month": "string",
      "total_revenue": 0
     }
    ]

    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """
    try:
        return (
            df.groupby(["hotel", "arrival_date_month"])["adr"]
            .sum()
            .reset_index(name="total_revenue")
            .rename(columns={"arrival_date_month": "month"})
            .to_dict("records")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_10
@app.get(
    "/bookings/top_countries/",
    summary="Get top 5 countries with the most bookings",
    response_model=list[TopCountries],
    tags=["Bookings"],
    status_code=200,
)
async def get_top_countries() -> list:
    """
    Retrieves the top 5 countries with the highest number of bookings.

    return: The top 5 countries with the most bookings.

    Expected response format:
    [
     {
      "country": "string",
      "number_of_bookings": 0
     }
    ]

    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """

    try:
        return (
            df.country.value_counts()
            .head()
            .reset_index(name="number_of_bookings")
            .to_dict("records")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_11
@app.get(
    "/bookings/repeated_guests_percentage/",
    summary="Get percentage of repeated guests",
    response_model=RepeatedGuestsPercentage,
    tags=["Bookings"],
    status_code=200,
)
async def get_repeated_guests_percentage() -> dict:
    """
    Retrieves the percentage of repeated guests among all bookings.

    return: The percentage of repeated guests.

    Expected response format:
    {"percentage_repeated_guests": 0}

    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """

    try:
        percent_repeat = (
            df.is_repeated_guest.value_counts()[1]
            / df.is_repeated_guest.value_counts()[0]
            * 100
        )
        return {"percentage_repeated_guests": percent_repeat}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_12
@app.get(
    "/bookings/total_guests_by_year/",
    summary="Get total number of guests by booking year",
    response_model=list[TotalGuestsByYearResponse],
    tags=["Bookings"],
    status_code=200,
)
async def get_total_guests_by_year() -> list:
    """
    Retrieves the total number of guests (adults, children, and babies) by booking year.

    return: The total number of guests by booking year

    Expected response format:
    [
     {
      "year": 0,
      "total_guests": 0
     }
    ]

    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """

    try:
        # group and filter by specified conditions
        total_number = (
            df.groupby("arrival_date_year")[["adults", "children", "babies"]]
            .sum()
            .sum(axis=1)
            .reset_index(name="total_guests")
            .rename(columns={"arrival_date_year": "year"})
        )

        # transform the data into the format corresponding to the expected response
        count_data_response = total_number.to_dict("records")

        return count_data_response

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_13
@app.get(
    "/bookings/avg_daily_rate_resort/",
    summary="Get average daily rate by month for resort hotel bookings",
    response_model=list[AvgDailyRateResort],
    tags=["Bookings"],
    status_code=200,
)
async def get_avg_daily_rate_resort(
    credentials: HTTPBasicCredentials = Security(verify_credentials),
) -> list:
    """
    Retrieves the average daily rate by month for resort hotel bookings.

    Return: The average daily rate by month for resort hotel bookings.

    Expected response format:
    [
     {
      "arrival_date_month": "string",
      "average_daily_rate": 0
     }
    ]

    HTTP Response Codes:
    - 200 OK: Successfuly received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """

    try:
        new_df = df.query("hotel == 'Resort Hotel'")

        return (
            new_df.groupby("arrival_date_month")["adr"]
            .mean()
            .reset_index(name="average_daily_rate")
            .to_dict(orient="records")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_14
@app.get(
    "/bookings/most_common_arrival_day_city/",
    summary="Get most common arrival date day of the week for city hotel bookings",
    response_model=MostCommonArrivalDayCity,
    tags=["Bookings"],
    status_code=200,
)
async def get_most_common_arrival_day_city(
    credentials: HTTPBasicCredentials = Security(verify_credentials),
) -> dict:
    """
    Retrieves the most common arrival date day of the week for city hotel bookings.

    Return: The most common arrival date day of the week for city hotel bookings.

    Expected response format:
    {"most_common_day": "string"}

    HTTP Response Codes:
    - 200 OK: Successfuly received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """

    try:
        new_df = df.query("hotel == 'City Hotel'")

        # creating a new column with conversion to date format  --> 2015-07-01
        new_df["arrival_date"] = pd.to_datetime(
            new_df["arrival_date_year"].astype(str)
            + "-"
            + new_df["arrival_date_month"]
            + "-"
            + new_df["arrival_date_day_of_month"].astype(str)
        )

        # creating a new column with conversion to date-of-day format --> Wednesday
        new_df["day_of_week"] = new_df.arrival_date.dt.day_name()

        # finding the most common day of the week
        most_common_day = new_df.day_of_week.mode().values[0]

        return {"most_common_day": most_common_day}

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_15
@app.get(
    "/bookings/count_by_hotel_meal/",
    summary="Get count of bookings by hotel type and meal package",
    response_model=list[CountByHotelMeal],
    tags=["Bookings"],
    status_code=200,
)
async def get_count_by_hotel_meal(
    credentials: HTTPBasicCredentials = Security(verify_credentials),
) -> list:
    """
    Retrieves the count of bookings grouped by hotel type and meal package.

    Return: The count of bookings by hotel type and meal package.

    Expected response format:
     [
      {
       "hotel": "string",
       "meal": "string",
       "count": 0
       }
     ]

    HTTP Response Codes:
    - 200 OK: Successfuly received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """

    try:
        return (
            df.groupby(["hotel", "meal"])
            .size()
            .reset_index(name="count")
            .to_dict(orient="records")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_16
@app.get(
    "/bookings/total_revenue_resort_by_country/",
    summary="Get total revenue by country for resort hotel bookings",
    response_model=list[TotalRevenueResortByCountry],
    tags=["Bookings"],
    status_code=200,
)
async def get_total_revenue_resort_by_country(
    credentials: HTTPBasicCredentials = Security(verify_credentials),
) -> list:
    """
    Retrieves the total revenue by country for resort hotel bookings.

    Return: The total revenue by country for resort hotel bookings.

    Expected response format:
    [
      {
      "country": "string",
      "total_revenue": 0
      }
    ]

    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """
    try:
        new_df = df.query("hotel == 'Resort Hotel'")

        return (
            new_df.groupby("country")["adr"]
            .sum()
            .reset_index(name="total_revenue")
            .to_dict(orient="records")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# URL_17
@app.get(
    "/bookings/count_by_hotel_repeated_guest/",
    summary="Get count of bookings by hotel type and repeated guest status",
    response_model=list[CountByHotelRepeatedGuestResponse],
    tags=["Bookings"],
    status_code=200,
)
async def get_count_by_hotel_repeated_guest(
    credentials: HTTPBasicCredentials = Security(verify_credentials),
) -> list:
    """
    Retrieves the count of bookings grouped by hotel type and repeated guest status.

    Return: The count of bookings by hotel type and repeated guest status.

    Expected response format:
    [
     {
       "hotel": "string",
       "is_repeated_guest": 0,
       "count": 0
      }
     ]

    HTTP Response Codes:
    - 200 OK: Successfully received the total number of guests.
    - 500 Internal Server Error: Internal server error.
    """

    try:
        return (
            df.groupby(["hotel", "is_repeated_guest"])
            .size()
            .reset_index(name="count")
            .to_dict(orient="records")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Run the FastAPI application
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
