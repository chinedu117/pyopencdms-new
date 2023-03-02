import pytest
from sqlalchemy import create_engine, schema
from sqlalchemy.orm import sessionmaker, close_all_sessions, Session, clear_mappers
from sqlalchemy.sql import text as sa_text
from opencdms.utils.db import get_cdm_connection_string
from opencdms.provider.opencdmsdb import mapper_registry, start_mappers
from opencdms.models import cdm
from datetime import datetime,timedelta
from uuid import uuid4
from faker import Faker
from cdms_pygeoapi import CDMSProvider
from pygeoapi.provider.base import (
    BaseProvider,
    ProviderConnectionError,
    ProviderQueryError,
    ProviderItemNotFoundError,
)
DB_URL = get_cdm_connection_string()

db_engine = create_engine(DB_URL)
Base = mapper_registry.generate_base()

@pytest.fixture
def db_session():
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


def setup_module(module):
    schemas = {v.schema for k, v in Base.metadata.tables.items()}

    for _schema in schemas:
        if not db_engine.dialect.has_schema(db_engine, _schema):
            db_engine.execute(schema.CreateSchema(_schema))
    Base.metadata.create_all(bind=db_engine)
    start_mappers()


def teardown_module(module):
    close_all_sessions()
    Base.metadata.drop_all(bind=db_engine)
    clear_mappers()

def create_observations(db_session: Session):
    feature_type = cdm.FeatureType( \
        name="Feature1", \
            description="A type of feature", \
                links=["https://links.features.com/1"]
            )
    user = cdm.User(
        id=str(uuid4()),
        name="John Doe"
    )
    status = cdm.RecordStatus(
        id=1,
        name="ACCEPTED",
        description="Valid record"
        )
    
    time_zone = cdm.TimeZone(abbreviation="UTC",name="lagos/africa",offset="1")
    source_type = cdm.SourceType(
        id=str(uuid4()),
        description="A source type"
    )
    db_session.add(source_type)
    db_session.add(feature_type)
    db_session.add(user)
    db_session.add(status)
    db_session.add(time_zone)
    db_session.commit()


    feature = cdm.Feature(
        id=str(uuid4()),
        type_id=feature_type.id,
        elevation=2.9,
        name="FEATURE2",
        geometry="POINT(-71.060316 48.432044)",
        description="A description"
    )
    collection = cdm.Collection(
        id=str(uuid4()),
        name="Collection 1",
        links=[" A link"]
    )

    observer = cdm.Observer(
        id=str(uuid4()),
        description="A good observer",
        links=["A link"],
        location="POINT(-71.060316 48.432044)",
        name = "An observer",
        elevation=3.2,
        manufacturer="phillips",
        model="AIOP",
        serial_number="12JKOP",
        firmware_version="45",
        uncertainty="OPI",
        observing_method="STANDING"
    )

    host = cdm.Host(
        id=str(uuid4()),
        name="Host Zone",
        version=1,
        change_date=datetime.utcnow(),
        user_id=user.id,
        comments="A comment",
        status_id=status.id,
        description="A nice host",
        links=["A link", "Another link"],
        location="POINT(-71.060316 48.432044)",
        elevation=3.8,
        wigos_station_identifier="WIGOD9",
        facility_type="modular",
        date_established=(datetime.utcnow() - timedelta(days=100)),
        date_closed=datetime.utcnow(),
        wmo_region="EAST",
        territory="UK",
        valid_from=datetime.utcnow(),
        valid_to=datetime.utcnow(),
        time_zone_id=time_zone.id
    )


    source = cdm.Source(
        id=str(uuid4()),
        name="Source 1",
        source_type_id=source_type.id,
        links=["A link"],
        processor='processor',
    )
    db_session.add(source)
    db_session.add(host)
    db_session.add(feature)
    db_session.add(collection)
    db_session.add(observer)
    db_session.commit()

    
    def _create_observations(lon: float, lat: float):
        observation_id = str(uuid4())
        observation = cdm.Observation(
            id=observation_id,
            location=cdm.Observation.set_location(lon, lat),
            version=1,
            change_date=datetime.utcnow(),
            comments="A simple observation",
            phenomenon_start=datetime.utcnow(),
            phenomenon_end=(datetime.utcnow()+ timedelta(days=1)),
            result_value=5.920399,
            feature_of_interest_id=feature.id,
            collection_id=collection.id,
            elevation=5.9,
            observer_id=observer.id,
            host_id=host.id,
            result_description="A good result",
            result_uom="uom",
            valid_from=datetime.utcnow(),
            valid_to=(datetime.utcnow()+ timedelta(days=1)),
            source_id=source.id,
            status_id=status.id,
            user_id=user.id,
            observation_type_id=None,
            result_quality=["good"],
            result_time=datetime.utcnow(),
            observed_property_id=None,
            observing_procedure_id=None,
            report_id=None,
            parameter=None

        )
        return observation

    fake = Faker()
    Faker.seed(0)
    observations = []
    # Create 10 observations from US coords
    for _ in range(10):
        lat, lon = fake.local_latlng("US",True)
        obs = _create_observations(float(lon), float(lat))
        observations.append(obs)
    # Create 10 obs from Nigeria
    for _ in range(10):
        lat, lon = fake.local_latlng("NG",True)
        obs = _create_observations(float(lon), float(lat))
        observations.append(obs)
    db_session.add_all(observations)
    db_session.commit()
    
    return True

def test_create_observations(db_session):
    created = create_observations(db_session)
    assert created is True


@pytest.fixture()
def config():
    return {
        'name': 'PostgreSQL',
        'type': 'feature',
        'data': {'host': '127.0.0.1',
                 'dbname': 'postgres',
                 'user': 'postgres',
                 "port": 35432,
                 'password': "password",
                 'search_path': ['cdm', 'public']
                 },
        'id_field': 'id',
        'table': 'observation',
        'geom_field': 'location'
    }


def test_query_should_show_selected_fields(config):
    # pytest.set_trace()
    """Test query with select properties"""
    p = CDMSProvider(config)
    select_properties=['comments','host_id']
    feature_collection = p.query(select_properties=select_properties)
    assert feature_collection.get('type') == 'FeatureCollection'
    features = feature_collection.get('features')
    assert features is not None
    feature = features[0]
    properties = feature.get('properties')
    assert select_properties[0] in properties.keys()
    assert properties is not None
    geometry = feature.get('geometry')
    assert geometry is not None

def test_query_with_property_filter(config):
    """Test query valid features when filtering by property"""
    p = CDMSProvider(config)
    properties=[("result_description","A good result" )]
    select_properties = ["result_description"]
    feature_collection = p.query(properties=properties, select_properties=select_properties)
    assert feature_collection.get('type') == 'FeatureCollection'
    features = feature_collection.get('features')
    assert features is not None
    feature = features[0]
    properties = feature.get('properties')
    assert select_properties[0] in properties.keys()
    assert properties is not None
    geometry = feature.get('geometry')
    assert geometry is not None


def test_query_bbox(config):
    """Test query with a specified bounding box """
    p = CDMSProvider(config)
    properties=[("result_description","A good result" )]
    select_properties = ["result_description"]
    NG_bbox = [ 2.69170169436, 4.24059418377, 14.5771777686, 13.8659239771 ] # Nigeria https://gist.github.com/graydon/11198540
    feature_collection = p.query(bbox=NG_bbox)
    features = feature_collection.get('features')
    assert len(features) == 10

def test_instantiation(config):
    """Test attributes are correctly set during instantiation."""
    # Act
    provider =CDMSProvider(config)

    # Assert
    assert provider.name == "PostgreSQL"
    assert provider.table == "observation"
    assert provider.id_field == "id"


def test_query_skip_geometry(config):
    """Test query without geometry"""
    p = CDMSProvider(config)
    result = p.query(skip_geometry=True)
    feature = result['features'][0]
    assert feature['geometry'] is None

def test_get_not_existing_item_raise_exception(config):
    """Testing query for a not existing object"""
    p = CDMSProvider(config)
    with pytest.raises(ProviderItemNotFoundError):
        p.get("2329039")