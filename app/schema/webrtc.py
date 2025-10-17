from typing import Annotated

from pydantic import BaseModel, Field


class WebRTCStats(BaseModel):
    round_trip_time: Annotated[float, Field(description="Round-trip time (seconds)")]
