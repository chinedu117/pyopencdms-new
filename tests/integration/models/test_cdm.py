import pytest
from sqlalchemy import create_engine, schema
from sqlalchemy.orm import sessionmaker, close_all_sessions, clear_mappers
from sqlalchemy.sql import text as sa_text
from opencdms.utils.db import get_cdm_connection_string
from opencdms.provider.opencdmsdb import mapper_registry, start_mappers
from opencdms.models import cdm
from datetime import datetime,timedelta
from uuid import uuid4

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

def test_create_feature(db_session):
    feature1 = cdm.FeatureType( \
        name="Feature1", \
            description="A type of feature", \
                links=["https://links.features.com/1"]
            )
    db_session.add(feature1)
    db_session.commit()
    feature_types = db_session.query(cdm.FeatureType).all()
    assert type(feature1.id) is int
    assert len(feature_types) == 1


def test_should_create_observation_type(db_session):
    obs_type_1 = cdm.ObservationType( \
        id=None,
        name="Observation1", \
        description="A type of observation_type", \
        links=["https://links.observation_types.com/1"]
            )
    db_session.add(obs_type_1)
    db_session.commit()

    assert type(obs_type_1.id) is int
    obs_types = db_session.query(cdm.ObservationType).all()
    assert len(obs_types) == 1


def test_should_create_observation(db_session):
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

    


    observation_id = str(uuid4())
    observation = cdm.Observation(
        id=observation_id,
        location=cdm.Observation.set_location(longitude=-71.060316,latitude=48.432044),
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
    db_session.add(observation)
    db_session.commit()
    observation = db_session.query(cdm.Observation).filter(cdm.Observation.id == observation_id).one()
   
    
