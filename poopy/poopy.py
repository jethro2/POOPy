import datetime
import warnings
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pooch
from geojson import MultiLineString, Feature, FeatureCollection, Point
from matplotlib.colors import LogNorm

from poopy.d8_accumulator import D8Accumulator


class Monitor:
    """A class to represent a CSO monitor.

    Attributes:
        site_name: The name of the site.
        permit_number: The permit number of the monitor.
        x_coord: The X coordinate of the site.
        y_coord: The Y coordinate of the site.
        receiving_watercourse: The receiving watercourse of the site.
        water_company: The water company that the monitor belongs to.
        current_status: The current status of the monitor.
        discharge_in_last_48h: Whether the monitor has discharged in the last 48 hours.
        current_event: The current event at the monitor.
        history: The history of events at the monitor.

    Methods:
        print_status: Print the current status of the monitor.
        get_history: Get the historical discharge information for the monitor and store it in the history attribute.
        plot_history: Plot the history of events at the monitor. Optionally specify a start date to plot from.
        total_discharge: Returns the total discharge in minutes since the given datetime.
        total_discharge_last_6_months: Returns the total discharge in minutes in the last 6 months (183 days)
        total_discharge_last_12_months: Returns the total discharge in minutes in the last 12 months (365 days)
        total_discharge_since_start_of_year: Returns the total discharge in minutes since the start of the year
        event_at: Returns the event that was occurring at the given time for the given monitor.
    """

    def __init__(
        self,
        site_name: str,
        permit_number: str,
        x_coord: float,
        y_coord: float,
        receiving_watercourse: str,
        water_company: "WaterCompany",
        discharge_in_last_48h: Optional[bool] = None,
    ) -> None:
        """
        Initialize attributes to describe a CSO monitor.

        Args:
            site_name: The name of the site.
            permit_number: The permit number of the monitor.
            x_coord: The X coordinate of the site.
            y_coord: The Y coordinate of the site.
            receiving_watercourse: The receiving watercourse of the site.
            water_company: The water company that the monitor belongs to.
            discharge_in_last_48h: Whether the monitor has discharged in the last 48 hours.
        """
        self._site_name: str = site_name
        self._permit_number: str = permit_number
        self._x_coord: float = x_coord
        self._y_coord: float = y_coord
        self._receiving_watercourse: str = receiving_watercourse
        self._water_company: WaterCompany = water_company
        self._discharge_in_last_48h: bool = discharge_in_last_48h
        self._current_event: Event = None
        self._history: List[Event] = None

    @property
    def site_name(self) -> str:
        """Return the name of the site."""
        return self._site_name

    @property
    def permit_number(self) -> str:
        """Return the permit number of the monitor."""
        return self._permit_number

    @property
    def x_coord(self) -> float:
        """Return the X coordinate of the site."""
        return self._x_coord

    @property
    def y_coord(self) -> float:
        """Return the Y coordinate of the site."""
        return self._y_coord

    @property
    def receiving_watercourse(self) -> str:
        """Return the receiving watercourse of the site."""
        return self._receiving_watercourse

    @property
    def water_company(self) -> "WaterCompany":
        """Return the water company that the monitor belongs to."""
        return self._water_company

    @property
    def current_status(self) -> str:
        """Return the current status of the monitor."""
        return self._current_event.event_type

    @property
    def current_event(self) -> "Event":
        """Return the current event of the monitor.

        Raises:
            ValueError: If the current event is not set.
        """
        if self._current_event is None:
            raise ValueError("Current event is not set.")
        return self._current_event

    def get_history(self) -> None:
        """
        Get the historical data for the monitor and store it in the history attribute.
        """
        self._history = self.water_company._get_monitor_history(self)

    @property
    def history(self) -> List["Event"]:
        """Return a list of all past events at the monitor.

        Raises:
            ValueError: If the history is not yet set.
        """
        if self._history is None:
            raise ValueError("History is not yet set!")
        return self._history

    @property
    def discharge_in_last_48h(self) -> bool:
        # Raise a warning if the discharge_in_last_48h is not set
        if self._discharge_in_last_48h is None:
            warnings.warn("discharge_in_last_48h is not set. Returning None.")
        return self._discharge_in_last_48h

    @current_event.setter
    def current_event(self, event: "Event") -> None:
        """Set the current event of the monitor.

        Raises:
            ValueError: If the current event is not ongoing.
        """
        if not event.ongoing:
            raise ValueError("Current Event must be ongoing.")
        else:
            self._current_event = event

    def print_status(self) -> None:
        """Print the current status of the monitor."""
        if self._current_event is None:
            print("No current event at this Monitor.")
        self._current_event.print()

    def total_discharge(self, since: datetime.datetime = None) -> float:
        """Returns the total discharge in minutes since the given datetime.
        If no datetime is given, it will return the total discharge since records began
        """
        history = self.history
        total = 0.0
        if since is None:
            since = datetime.datetime(2000, 1, 1)  # A long time ago
        for event in history:
            if event.event_type == "Discharging":
                if event.ongoing:
                    if event.start_time < since:
                        # If the start time is before the cut off date, we can take the difference between the current time and the cut off date
                        total += (datetime.datetime.now() - since).total_seconds() / 60
                    else:
                        total += event.duration
                else:
                    # If the end time is before the cut off date, we can skip this event
                    if event.end_time < since:
                        continue
                    # If the endtime is after since but start_time is before, we take the difference between the end time and since
                    elif (event.end_time > since) and (event.start_time < since):
                        total += (event.end_time - since).total_seconds() / 60
                    elif event.end_time > since:
                        total += event.duration
        return total

    def total_discharge_last_6_months(self) -> float:
        """Returns the total discharge in minutes in the last 6 months (183 days)"""
        return self.total_discharge(
            since=datetime.datetime.now() - datetime.timedelta(days=183)
        )

    def total_discharge_last_12_months(self) -> float:
        """Returns the total discharge in minutes in the last 12 months (365 days)"""
        return self.total_discharge(
            since=datetime.datetime.now() - datetime.timedelta(days=365)
        )

    def total_discharge_since_start_of_year(self) -> float:
        """Returns the total discharge in minutes since the start of the year"""
        return self.total_discharge(
            since=datetime.datetime(datetime.datetime.now().year, 1, 1)
        )

    def plot_history(self, since: datetime.datetime = None) -> None:
        """Plot the history of events at the monitor. Optionally specify a start date to plot from.
        If no start date is specified, it will plot from the first recorded Discharge or Offline event.
        If no events are recorded for that monitor, no plot will be returned and a warning will be raised.
        """
        events = self.history
        if len(events) == 0:
            warnings.warn(
                "\033[91m"
                + f"\n!WARNING! Monitor {self.site_name} has no recorded events. Returning None."
                + "\033[0m"
            )

        else:
            plt.figure(figsize=(10, 2))
            for event in events:
                start = event.start_time
                if event.ongoing:
                    end = datetime.datetime.now()
                else:
                    end = event.end_time
                if event.event_type == "Discharging":
                    color = "#8B4513"
                if event.event_type == "Offline":
                    color = "grey"
                if event.event_type == "Not Discharging":
                    continue

                # Create a figure that is wide and not very tall
                # Plot a polygon for each event that extends from the start to the end of the event
                # and from y = 0 to y = 1
                plt.fill_between([start, end], 0, 1, color=color)
                # Set the title to the name of the monitor
            # Remove all y axis ticks and labels
            plt.yticks([])
            plt.ylabel("")
            plt.ylim(0, 1)
            # Set the x axis limits to the start and end of the event list
            if since is None:
                minx, maxx = events[-1].start_time, datetime.datetime.now()
            else:
                minx, maxx = since, datetime.datetime.now()
            plt.xlim(minx, maxx)
            total_discharge = self.total_discharge(since=since)
            plt.title(
                self.site_name
                + "\n"
                + f"Total Discharge: {round(total_discharge,2)} minutes"
            )
            plt.tight_layout()
            plt.show()

    def event_at(self, time: datetime.datetime) -> Union[None, "Event"]:
        """
        Returns the event that is ongoing at the given time for the given monitor.
        If no event is found (e.g., the time was before a monitor was installed), it returns None.

        Args:
            time: The time to check for an event.

        Returns:
            The event that is ongoing at the given time for the given monitor.
        """
        out = None
        for event in self.history:
            if event.ongoing and time > event.start_time:
                # If the event is ongoing and the time is after the start time, then it is the current event
                out = event
            elif event.start_time < time and time < event.end_time:
                # If the event is not ongoing but the time is between the start and end time, then it is the current event
                out = event
        return out

    def _history_masks(
        self, times: List[datetime.datetime]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        online = np.zeros(len(times), dtype=bool)
        active = np.zeros(len(times), dtype=bool)
        recent = np.zeros(len(times), dtype=bool)
        """
        Returns three boolean arrays that indicate, respectively, whether the monitor was online, active, 
        or recently active (within 48 hours) at each time given in the times list. The times list should be
        regularly spaced in 15 minute intervals. The arrays are returned in the same order as the times list.
        This is a hidden method that is used by the get_monitor_timeseries() method in the WaterCompany class.

        Args:
            times: A list of times to check the monitor status at.

        Returns:
            A tuple of three boolean arrays indicating whether the monitor was online, active, or recently active.  
        
        """

        if len(self.history) == 0:
            print(f"Monitor {self.site_name} has no recorded events")
            return online, active, recent

        first_event = round_time_down_15(self.history[-1].start_time)
        # If first event is before the first time in the times list, then we need to fill the online array with 1s
        if first_event < times[0]:
            online[:] = True
        else:
            online[times.index(first_event) :] = True

        for event in self.history:
            if event.event_type == "Discharging" or event.event_type == "Offline":
                start_round = round_time_down_15(event.start_time)
                if start_round < times[0]:
                    # Quit loop if start_round is before the first time in the times list
                    break
                if event.ongoing:
                    # If the event is ongoing, then we can set the active array to True from the start_round to the end of
                    # the array
                    if event.event_type == "Discharging":
                        active[times.index(start_round) :] = True
                        recent[times.index(start_round) :] = True
                    else:
                        online[times.index(start_round) :] = False
                else:
                    # If the event is not ongoing, then we can set the active array to True from the start_round to the
                    # end_round
                    end_round = round_time_up_15(event.end_time)
                    if event.event_type == "Discharging":
                        active[times.index(start_round) : times.index(end_round)] = True
                        # Set recent to True from start_round to 48 hours after end_round
                        recent_end = end_round + datetime.timedelta(hours=48)
                        if recent_end > times[-1]:
                            # If recent_end is after the end of the array, then set recent to True from start_round to the end of the array
                            recent[times.index(start_round) :] = True
                        else:
                            recent[
                                times.index(start_round) : times.index(recent_end)
                            ] = True
                    else:
                        online[
                            times.index(start_round) : times.index(end_round)
                        ] = False

        return online, active, recent


class Event(ABC):
    """A class to represent an event at a CSO monitor.

    Attributes:
        monitor: The monitor at which the event occurred.
        ongoing: Whether the event is ongoing.
        start_time: The start time of the event.
        end_time: The end time of the event.
        duration: The duration of the event.
        event_type: The type of event.

    Methods:
        summary: Print a summary of the event.

    """

    @abstractmethod
    def __init__(
        self,
        monitor: Monitor,
        ongoing: bool,
        start_time: datetime.datetime,
        end_time: Optional[datetime.datetime] = None,
        event_type: Optional[str] = "Unknown",
    ) -> None:
        """
        Initialize attributes to describe an event.

        Args:
            monitor: The monitor at which the event occurred.
            ongoing: Whether the event is ongoing.
            start_time: The start time of the event.
            end_time: The end time of the event. Defaults to None.
            event_type: The type of event. Defaults to "Unknown".

        Methods:
            print: Print a summary of the event.
        """
        self._monitor = monitor
        self._start_time = start_time
        self._ongoing = ongoing
        self._end_time = end_time
        self._duration = self.duration
        self._event_type = event_type
        self._validate()

    def _validate(self):
        """Validate the attributes of the event.

        Raises:
            ValueError: If the end time is before the start time.
            ValueError: If the end time is not None and the event is ongoing.
        """
        if self._ongoing and self._end_time is not None:
            raise ValueError("End time must be None if the event is ongoing.")
        if self._end_time is not None and self._end_time < self._start_time:
            raise ValueError("End time must be after the start time.")

    @property
    def duration(self) -> float:
        """Return the duration of the event in minutes."""
        if self._start_time is not None:
            if not self.ongoing:
                return (self._end_time - self._start_time).total_seconds() / 60
            else:
                return (datetime.datetime.now() - self._start_time).total_seconds() / 60
        else:
            return 0

    @property
    def ongoing(self) -> bool:
        """Return if the event is ongoing."""
        return self._ongoing

    @property
    def start_time(self) -> Optional[datetime.datetime]:
        """Return the start time of the event."""
        return self._start_time

    @property
    def end_time(self) -> Union[datetime.datetime, None]:
        """Return the end time of the event."""
        # If the event is Ongoing raise a Warning that the event is ongoing and has no end time but allow program to continue
        if self._ongoing:
            warnings.warn(
                "\033[91m"
                + "!WARNING! Event is ongoing and has no end time. Returning None."
                + "\033[0m"
            )
        return self._end_time

    @property
    def event_type(self) -> str:
        """Return the type of event."""
        return self._event_type

    @property
    def monitor(self) -> Monitor:
        """Return the monitor at which the event occurred."""
        return self._monitor

    # Define a setter for ongoing that only allows setting to False. It then sets the end time to the current time, and calculates the duration.
    @ongoing.setter
    def ongoing(self, value: bool) -> None:
        """Set the ongoing status of the event.

        Args:
            value: The value to set the ongoing status to.

        Raises:
            ValueError: If the ongoing status is already False.
            ValueError: If the event is already not ongoing.
        """
        if value:
            raise ValueError("Ongoing status can only be set to False.")
        # Check if the discharge event is already not ongoing
        if not self._ongoing:
            raise ValueError("Event is already not ongoing.")
        else:
            self._ongoing = value
            self._end_time = datetime.datetime.now()
            self._duration = self.duration

    def print(self) -> None:
        """Print a summary of the event."""

        # Define a dictionary of colours for the event types
        event_type_colour = {
            "Discharging": "\033[31m",  # Red
            "Offline": "\033[30m",  # Black
            "Not Discharging": "\033[32m",  # Green
            "Unknown": "\033[0m",  # Default
        }

        print(
            f"""
        {event_type_colour[self.event_type]}
        --------------------------------------
        Event Type: {self.event_type}
        Site Name: {self.monitor.site_name}
        Permit Number: {self.monitor.permit_number}
        OSGB Coordinates: ({self.monitor.x_coord}, {self.monitor.y_coord})
        Receiving Watercourse: {self.monitor.receiving_watercourse}
        Start Time: {self.start_time}
        End Time: {self.end_time if not self.ongoing else "Ongoing"}
        Duration: {round(self.duration,2)} minutes\033[0m
        """
        )


class Discharge(Event):
    """A class to represent a discharge event at a CSO."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._event_type = "Discharging"

    def _to_row(self) -> pd.DataFrame:
        """
        Convert a discharge event to a row in a dataframe.
        """
        row = pd.DataFrame(
            {
                "LocationName": self.monitor.site_name,
                "PermitNumber": self.monitor.permit_number,
                "X": self.monitor.x_coord,
                "Y": self.monitor.y_coord,
                "ReceivingWaterCourse": self.monitor.receiving_watercourse,
                "StartDateTime": self.start_time,
                "StopDateTime": self.end_time,
                "Duration": self.duration,
                "OngoingDischarge": self.ongoing,
            },
            index=[0],
        )
        return row


class Offline(Event):
    """A class to represent a CSO monitor being offline."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._event_type = "Offline"


class NoDischarge(Event):
    """A class to represent a CSO not discharging."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._event_type = "Not Discharging"


class WaterCompany(ABC):
    """
    A class that represents the EDM monitoring network for a Water Company.

    Attributes:
        name: The name of the Water Company network (set by the child class).
        timestamp: The timestamp of the last update.
        history_timestamp: The timestamp of the last historical data update (set in the `get_history` method of the child class).
        clientID: The client ID for the Water Company API (set by the child class).
        clientSecret: The client secret for the Water Company API (set by the child class).
        active_monitors: A dictionary of active monitors accessed by site name.
        active_monitor_names: A list of the names of active monitors.
        accumulator: The D8 flow accumulator for the region of the water company.
        discharging_monitors: A list of all monitors that are currently recording a discharge event.
        recently_discharging_monitors: A list of all monitors that have discharged in the last 48 hours.
    Methods:
        update: Updates the active_monitors list and the timestamp.
        set_all_histories: Sets the historical data for all active monitors and store it in the history attribute of each monitor.
        history_to_discharge_df: Convert a water company's total discharge history to a dataframe
        get_downstream_geojson: Get a geojson of the downstream points for all active discharges in BNG coordinates.
        get_downstream_info_geojson: Get a GeoJSON feature collection of the downstream points for all active discharges in BNG coordinates.
        plot_current_status: Plot the current status of the Water Company network showing the downstream impact & monitor statuses.
    """

    def __init__(self, clientID: str, clientSecret: str):
        """
        Initialize attributes to describe a Water Company network.

        Args:
            clientID: The client ID for the Water Company API.
            clientSecret: The client secret for the Water Company API.
        """
        self._name: str = None
        self._clientID = clientID
        self._clientSecret = clientSecret
        self._active_monitors: Dict[str, Monitor] = self._fetch_active_monitors()
        self._timestamp: datetime.datetime = datetime.datetime.now()
        self._accumulator: D8Accumulator = None
        self._d8_file_path: str = None

    @abstractmethod
    def _fetch_active_monitors(self) -> Dict[str, Monitor]:
        """
        Get the current status of the monitors by calling the API.

        Returns:
            A dictionary of active monitors accessed by site name.
        """
        pass

    @abstractmethod
    def _get_monitor_history(self, monitor: Monitor) -> List[Event]:
        """
        Get the history of events for a monitor.

        Args:
            monitor: The monitor for which to get the history.

        Returns:
            A list of events.
        """
        pass

    @abstractmethod
    def set_all_histories(self) -> None:
        """
        Sets the historical data for all active monitors and store it in the history attribute of each monitor.
        """
        pass

    def _fetch_d8_file(self, url: str, known_hash: str) -> str:
        """
        Get the path to the D8 file for the catchment. If the file is not present, it will download it from the given url.
        This is all handled by the pooch package. The hash of the file is checked against the known hash to ensure the file is not corrupted.
        If the file is already present in the pooch cache, it will not be downloaded again.
        """
        file_path = pooch.retrieve(url=url, known_hash=known_hash)

        return file_path

    # Define the getters for the WaterCompany class
    @property
    def name(self) -> str:
        """Return the name of the Water Company network."""
        return self._name

    @property
    def timestamp(self) -> datetime.datetime:
        """Return the timestamp of the last update."""
        return self._timestamp

    @property
    def history_timestamp(self) -> datetime.datetime:
        """Return the timestamp of the last historical data update."""
        return self._history_timestamp

    @property
    def clientID(self) -> str:
        """Return the client ID for the API."""
        return self._clientID

    @property
    def clientSecret(self) -> str:
        """Return the client secret for the API."""
        return self._clientSecret

    @property
    def active_monitors(self) -> List[Monitor]:
        """Return the active monitors."""
        return self._active_monitors

    @property
    def active_monitor_names(self) -> List[str]:
        """Return the names of active monitors."""
        return list(self._active_monitors.keys())

    @property
    def discharging_monitors(self) -> List[Monitor]:
        """Return a list of all monitors that are currently recording a discharge event."""
        return [
            monitor
            for monitor in self._active_monitors.values()
            if monitor.current_status == "Discharging"
        ]

    @property
    def recently_discharging_monitors(self) -> List[Monitor]:
        """Return a list of all monitors that have discharged in the last 48 hours."""
        return [
            monitor
            for monitor in self._active_monitors.values()
            if monitor.discharge_in_last_48h
        ]

    @property
    def accumulator(self) -> D8Accumulator:
        """Return the D8 flow accumulator for the area of the water company."""
        if self._accumulator is None:
            self._accumulator = D8Accumulator(self._d8_file_path)
        return self._accumulator

    def update(self):
        """
        Update the active_monitors list and the timestamp.
        """
        self._active_monitors = self._fetch_active_monitors()
        self._timestamp = datetime.datetime.now()

    def _calculate_downstream_impact(
        self, include_recent_discharges: bool = False
    ) -> None:
        """
        Calculate the downstream impact for all active discharges. Stores a 2D numpy array to the WaterCompany called 'num_upstream_discharges'
        that contains the number of upstream discharges at each point in the flow accumulator. The optional argument include_recent_discharges allows you to
        include discharges that have occurred in the last 48 hours. Defaults to False.

        This function returns None but stores the result (a 2D numpy array) in the WaterCompany object.

        Args:
            include_recent_discharges: Whether to include discharges that have occurred in the last 48 hours. Defaults to False.
        """

        # Extract all the xy coordinates of active discharges
        accumulator = self.accumulator
        # Coords of all active discharges in OSGB
        if not include_recent_discharges:
            source_nodes = [
                accumulator.coord_to_node(discharge.x_coord, discharge.y_coord)
                for discharge in self.discharging_monitors
            ]
        else:
            source_nodes = [
                accumulator.coord_to_node(discharge.x_coord, discharge.y_coord)
                for discharge in self.recently_discharging_monitors
            ]

        # Set up the source array for propagating discharges downstream
        source_array = np.zeros(accumulator.arr.shape).flatten()
        source_array[source_nodes] = 1
        source_array = source_array.reshape(accumulator.arr.shape)
        # Propagate the discharges downstream and add the result to the WaterCompany object
        return accumulator.accumulate(source_array)

    def get_downstream_geojson(
        self, include_recent_discharges: bool = False
    ) -> MultiLineString:
        """
        Get a MultiLineString of the downstream points for all active discharges in BNG coordinates.

        Args:
            include_recent_discharges: Whether to include discharges that have occurred in the last 48 hours. Defaults to False.

        Returns:
            A geojson MultiLineString of the downstream points for all active (or optionally recent) discharges.
        """
        # Calculate the downstream impact
        downstream_impact = self._calculate_downstream_impact(
            include_recent_discharges=include_recent_discharges
        )
        # Convert the downstream impact to a geojson
        return self._accumulator.get_channel_segments(downstream_impact, threshold=0.9)

    def get_downstream_info_geojson(
        self, include_recent_discharges=False
    ) -> FeatureCollection:
        """
        Get a GeoJSON feature collection of the downstream points for all active discharges in BNG coordinates.
        Each feature contains as properties: 1) the number of upstream discharges 2) the number of upstream discharges
        per km2 upstream and 3) a list of the active (or recent) discharging EDMs upstream.

        Args:
            include_recent_discharges: Whether to include discharges that have occurred in the last 48 hours. Defaults to False.

        Returns:
            A GeoJSON feature collection of the downstream points for all active (or optionally recent) discharges.
        """
        trsfm = self.accumulator.ds.GetGeoTransform()
        cell_area = (trsfm[1] * trsfm[5] * -1) / 1000000
        areas = np.ones(self.accumulator.arr.shape) * cell_area
        drainage_area = self.accumulator.accumulate(areas)
        impact = self._calculate_downstream_impact(
            include_recent_discharges=include_recent_discharges
        )
        impact_per_area = impact / drainage_area
        impact = impact.flatten()
        impact_per_area = impact_per_area.flatten()
        dstream_nodes = np.where(impact > 0)[0]

        # Create a dictionary of properties for each node
        dstream_info = {
            node: {
                "number_upstream_CSOs": impact[node],
                "number_CSOs_per_km2": impact_per_area[node],
                "CSOs": [],
            }
            for node in dstream_nodes
        }
        if include_recent_discharges:
            sources = self.recently_discharging_monitors
        else:
            sources = self.discharging_monitors

        # Add the sources for each impacted node to the dictionary of properties
        for monitor in sources:
            node = self.accumulator.coord_to_node(monitor.x_coord, monitor.y_coord)
            dstream, _ = self.accumulator.get_profile(node)
            for node in dstream:
                dstream_info[node]["CSOs"].append(monitor.site_name)

        # Create a list of coordinates and properties for each impacted node in the network
        coordinates = []
        properties = []
        for node in dstream_nodes:
            coord = self.accumulator.node_to_coord(node)
            coordinates.append(coord)
            properties.append(dstream_info[node])

        # Create a list of GeoJSON features from the coordinates and properties
        features = [
            Feature(geometry=Point(coord), properties=prop)
            for coord, prop in zip(coordinates, properties)
        ]
        # Create a GeoJSON feature collection from the list of features
        feature_collection = FeatureCollection(features)
        return feature_collection

    def get_monitor_timeseries(
        self, since: datetime.datetime
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns a pandas DataFrame containing timeseries of the number of CSOs that 1) were active, 2) were active in last
        48 hours, 3) online at a list of times every 15 minutes since the given datetime. This can be used to plot the
        number of active CSOs and monitors over time. NB that for "online" we conservatively assume that every monitor was
        _offline_ until we receive any positive event from it. This means that if a monitor is installed but recording
        'notdischarging' for a month until its first discharge event, it will be counted as offline for that month. Lacking
        any other information, this is the most conservative assumption we can make.

        Args:
            since: The datetime to start the timeseries from.

        Returns:
            A pandas DataFrame containing timeseries of the number of CSOs that 1) were active, 2) were active in last
            48 hours, 3) online at a list of times every 15 minutes since the given datetime.
        """
        times = []
        now = datetime.datetime.now()
        time = since
        while time < now:
            times.append(time)
            time += datetime.timedelta(minutes=15)

        active = np.zeros(len(times), dtype=int)
        recent = np.zeros(len(times), dtype=int)
        online = np.zeros(len(times), dtype=int)

        for monitor in self.active_monitors.values():
            print(f"Processing {monitor.site_name}")
            mon_online, mon_active, mon_recent = monitor._history_masks(times)
            active += mon_active.astype(int)
            recent += mon_recent.astype(int)
            online += mon_online.astype(int)

        return pd.DataFrame(
            {
                "datetime": times,
                "number_discharging": active,
                "number_recently_discharging": recent,
                "number_online": online,
            }
        )

    def plot_current_status(self) -> None:
        """
        Plot the current status of the Water Company network.
        """

        plt.figure(figsize=(11, 8))
        acc = self.accumulator
        geojson = self.get_downstream_geojson(include_recent_discharges=True)
        dx, dy = acc.ds.GetGeoTransform()[1], acc.ds.GetGeoTransform()[5]
        cell_area = dx * dy * -1
        upstream_area = acc.accumulate(weights=cell_area * np.ones(acc.arr.shape))

        # Plot the rivers
        plt.imshow(upstream_area, norm=LogNorm(), extent=acc.extent, cmap="Blues")
        # Add a hillshade
        plt.imshow(acc.arr, cmap="Greys_r", alpha=0.2, extent=acc.extent)
        for line in geojson.coordinates:
            x = [c[0] for c in line]
            y = [c[1] for c in line]
            plt.plot(x, y, color="brown", linewidth=2)

        # Plot the status of the monitors
        for monitor in self.active_monitors.values():
            if monitor.current_status == "Discharging":
                colour = "red"
                size = 100
            elif monitor.discharge_in_last_48h:
                colour = "orange"
                size = 50
            elif monitor.current_status == "Not Discharging":
                colour = "green"
                size = 10
            elif monitor.current_status == "Offline":
                colour = "grey"
                size = 25
            plt.scatter(
                monitor.x_coord,
                monitor.y_coord,
                color=colour,
                s=size,
                zorder=10,
                marker="x",
            )
        # Set the axis to be equal
        plt.axis("equal")
        plt.tight_layout()

        plt.xlabel("Easting (m)")
        plt.ylabel("Northing (m)")
        plt.title(self.name + ": " + self.timestamp.strftime("%Y-%m-%d %H:%M"))

    def history_to_discharge_df(self) -> pd.DataFrame:
        """
        Convert a water company's discharge history to a dataframe

        Returns:
            A dataframe of discharge events.

        Raises:
            ValueError: If the history is not yet set. Run set_all_histories() first.

        """
        if self.history_timestamp is None:
            raise ValueError(
                "History may not yet be set. Try running set_all_histories() first."
            )
        print("\033[36m" + f"Building output data-table" + "\033[0m")
        df = pd.DataFrame()
        for monitor in self.active_monitors.values():
            print("\033[36m" + f"\tProcessing {monitor.site_name}" + "\033[0m")
            for event in monitor.history:
                if event.event_type == "Discharging":
                    df = pd.concat([df, event._to_row()], ignore_index=True)

        df.sort_values(
            by="StartDateTime", inplace=True, ignore_index=True, ascending=False
        )
        return df


def round_time_down_15(time: datetime.datetime) -> datetime.datetime:
    """
    Rounds a datetime down to the nearest 15 minutes.
    """
    minutes = time.minute
    if minutes < 15:
        minutes = 0
    elif minutes < 30:
        minutes = 15
    elif minutes < 45:
        minutes = 30
    else:
        minutes = 45
    return datetime.datetime(time.year, time.month, time.day, time.hour, minutes, 0, 0)


def round_time_up_15(time: datetime.datetime) -> datetime.datetime:
    """
    Rounds a datetime up to the nearest 15 minutes.
    """
    minutes = time.minute
    if minutes < 15:
        minutes = 15
    elif minutes < 30:
        minutes = 30
    elif minutes < 45:
        minutes = 45
    else:
        minutes = 0
        time += datetime.timedelta(hours=1)
    return datetime.datetime(time.year, time.month, time.day, time.hour, minutes, 0, 0)
