import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import UUID, uuid5, NAMESPACE_DNS
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models import Complaint, Status
from app.providers.triage.base import Category, Priority

# Fixed namespace UUID for generating deterministic complaint IDs from seed data
SEED_NAMESPACE = uuid5(NAMESPACE_DNS, "civicpulse.pk")

SEED_COMPLAINTS = [
    # Water (6 complaints)
    {
        "seed_id": "water-01",
        "text": "Main water supply line burst ho gayi hai near Bilal Masjid. Paani ground floor houses me ghus raha hai since Fajr. Urgent help needed!",
        "location": "Street 12, Sector F-8/1, Islamabad",
        "reporter_contact": "0300-1122334",
        "category": Category.WATER,
        "priority": Priority.HIGH,
        "status": Status.OPEN,
        "ai_summary": "Burst water main flooding street and ground floor houses since Fajr.",
        "triaged_by": "rules",
        "triage_latency_ms": 142,
    },
    {
        "seed_id": "water-02",
        "text": "Severe water contamination in our pipeline. Ganda paani aa raha hai with bad smell since 3 days. Children falling sick.",
        "location": "Block C, North Nazimabad, Karachi",
        "reporter_contact": "0321-9988776",
        "category": Category.WATER,
        "priority": Priority.HIGH,
        "status": Status.IN_PROGRESS,
        "ai_summary": "Contaminated smelly tap water entering houses, causing sickness.",
        "triaged_by": "llm:groq",
        "triage_latency_ms": 350,
    },
    {
        "seed_id": "water-03",
        "text": "Water valve leakage in street corner. Clean drinking water wasted continuously on road. Plz send WASA team to repair.",
        "location": "Main Market, Gulberg II, Lahore",
        "reporter_contact": "gulberg.citizen@gmail.com",
        "category": Category.WATER,
        "priority": Priority.NORMAL,
        "status": Status.OPEN,
        "ai_summary": "Water valve leak wasting clean drinking water on street.",
        "triaged_by": "rules",
        "triage_latency_ms": 110,
    },
    {
        "seed_id": "water-04",
        "text": "No water supply in our mohallah for the past five days. Tanker mafia is charging 8000 rupees. Kindly restore line supply.",
        "location": "Sector 11-A, Orangi Town, Karachi",
        "reporter_contact": "0345-2233445",
        "category": Category.WATER,
        "priority": Priority.NORMAL,
        "status": Status.OPEN,
        "ai_summary": "Complete water outage for five days in Orangi Town residential block.",
        "triaged_by": "rules",
        "triage_latency_ms": 95,
    },
    {
        "seed_id": "water-05",
        "text": "Sewer line mixed with fresh drinking line near primary school. Danger of disease outbreak among students. Very urgent issue.",
        "location": "Circular Road near Govt High School, Rawalpindi",
        "reporter_contact": "headmaster.school@edu.pk",
        "category": Category.WATER,
        "priority": Priority.HIGH,
        "status": Status.OPEN,
        "ai_summary": "Sewerage cross-contamination into school fresh water line.",
        "triaged_by": "llm:gemini",
        "triage_latency_ms": 420,
    },
    {
        "seed_id": "water-06",
        "text": "Underground water reservoir lid broken and open. Small kids play nearby, danger of someone falling inside.",
        "location": "Family Park, Phase 4, Hayatabad, Peshawar",
        "reporter_contact": "0333-7766554",
        "category": Category.WATER,
        "priority": Priority.HIGH,
        "status": Status.RESOLVED,
        "ai_summary": "Open underground water reservoir lid in children park.",
        "triaged_by": "rules",
        "triage_latency_ms": 130,
    },

    # Electricity (6 complaints)
    {
        "seed_id": "elec-01",
        "text": "PMT transformer caught fire with loud blast. Heavy sparks falling on parked cars and shops. Send fire brigade and WAPDA immediately!",
        "location": "Barkat Market, New Garden Town, Lahore",
        "reporter_contact": "0301-4455667",
        "category": Category.ELECTRICITY,
        "priority": Priority.HIGH,
        "status": Status.IN_PROGRESS,
        "ai_summary": "Transformer fire with sparks dropping on commercial street.",
        "triaged_by": "rules",
        "triage_latency_ms": 115,
    },
    {
        "seed_id": "elec-02",
        "text": "High tension 11kV live electric wire broken and hanging at head height across the street. Extreme danger of electrocution in rain.",
        "location": "Gali 7, Dhok Kala Khan, Rawalpindi",
        "reporter_contact": "0312-5544332",
        "category": Category.ELECTRICITY,
        "priority": Priority.HIGH,
        "status": Status.OPEN,
        "ai_summary": "Live hanging 11kV wire posing imminent danger of electrocution.",
        "triaged_by": "rules:fallback",
        "triage_latency_ms": 1020,
    },
    {
        "seed_id": "elec-03",
        "text": "Low voltage issue since last week. Voltage fluctuating between 140V and 180V. ACs and refrigerators got damaged due to trip.",
        "location": "Sector G-13/2, Islamabad",
        "reporter_contact": "usman.engr@yahoo.com",
        "category": Category.ELECTRICITY,
        "priority": Priority.NORMAL,
        "status": Status.OPEN,
        "ai_summary": "Persistent low voltage causing home appliances damage.",
        "triaged_by": "rules",
        "triage_latency_ms": 88,
    },
    {
        "seed_id": "elec-04",
        "text": "Electricity feeder tripping repeatedly every 15 minutes. Entire mohalla suffering in extreme heatwave.",
        "location": "Gulshan-e-Iqbal Block 13-D, Karachi",
        "reporter_contact": "0300-9876543",
        "category": Category.ELECTRICITY,
        "priority": Priority.NORMAL,
        "status": Status.IN_PROGRESS,
        "ai_summary": "Repeated feeder tripping disrupting power during heatwave.",
        "triaged_by": "llm:groq",
        "triage_latency_ms": 280,
    },
    {
        "seed_id": "elec-05",
        "text": "Electric meter box door broken on footpath. Wires are exposed to rainwater puddles near bus stop.",
        "location": "Kachehri Chowk, Faisalabad",
        "reporter_contact": None,
        "category": Category.ELECTRICITY,
        "priority": Priority.HIGH,
        "status": Status.OPEN,
        "ai_summary": "Open meter box with exposed live connections in public water puddle.",
        "triaged_by": "rules",
        "triage_latency_ms": 120,
    },
    {
        "seed_id": "elec-06",
        "text": "Damaged electricity pole leaning dangerously towards residential house after trailer hit it last night.",
        "location": "Satyana Road, Peoples Colony, Faisalabad",
        "reporter_contact": "0346-6543210",
        "category": Category.ELECTRICITY,
        "priority": Priority.HIGH,
        "status": Status.RESOLVED,
        "ai_summary": "Tilted utility pole leaning on house following vehicular collision.",
        "triaged_by": "rules",
        "triage_latency_ms": 140,
    },

    # Sanitation (6 complaints)
    {
        "seed_id": "san-01",
        "text": "Open gutter manhole cover missing on main road. Two motorcyclists already slipped yesterday night. Fatal accident can happen anytime.",
        "location": "Korangi Road near CSD, DHA Phase 1, Karachi",
        "reporter_contact": "0333-2109876",
        "category": Category.SANITATION,
        "priority": Priority.HIGH,
        "status": Status.OPEN,
        "ai_summary": "Missing manhole cover on busy road causing bike accidents.",
        "triaged_by": "rules",
        "triage_latency_ms": 105,
    },
    {
        "seed_id": "san-02",
        "text": "Huge kachra kundi garbage dumping pile overflowing for 2 weeks. Stray dogs gathering, intolerable rotten smell spreading across society.",
        "location": "Allama Iqbal Town, Ravi Block, Lahore",
        "reporter_contact": "iqbaltown.rwa@gmail.com",
        "category": Category.SANITATION,
        "priority": Priority.NORMAL,
        "status": Status.OPEN,
        "ai_summary": "Overflowing community garbage dump uncleared for two weeks.",
        "triaged_by": "rules",
        "triage_latency_ms": 90,
    },
    {
        "seed_id": "san-03",
        "text": "Sewerage gutter line choked completely. Filthy black drain water flooded into residential street and entering front gates.",
        "location": "Street 4, Muslim Town, Rawalpindi",
        "reporter_contact": "0313-8899001",
        "category": Category.SANITATION,
        "priority": Priority.HIGH,
        "status": Status.IN_PROGRESS,
        "ai_summary": "Choked sewer line flooding black waste water into doorsteps.",
        "triaged_by": "llm:groq",
        "triage_latency_ms": 310,
    },
    {
        "seed_id": "san-04",
        "text": "Hospital hazardous waste and syringes dumped illegally in vacant plot adjacent to playground. Massive health biohazard.",
        "location": "Near DHQ Hospital, Gujranwala",
        "reporter_contact": "0302-3344556",
        "category": Category.SANITATION,
        "priority": Priority.HIGH,
        "status": Status.OPEN,
        "ai_summary": "Illegal dumping of clinical hospital waste near children playground.",
        "triaged_by": "rules",
        "triage_latency_ms": 125,
    },
    {
        "seed_id": "san-05",
        "text": "Sanitation sweepers have not visited street 18 for over 10 days. Leaf litter and domestic waste gathering in front of houses.",
        "location": "Street 18, Sector I-9/4, Islamabad",
        "reporter_contact": "0322-7711223",
        "category": Category.SANITATION,
        "priority": Priority.LOW,
        "status": Status.RESOLVED,
        "ai_summary": "Street sweeping neglected for ten days in residential sector.",
        "triaged_by": "rules",
        "triage_latency_ms": 98,
    },
    {
        "seed_id": "san-06",
        "text": "Dead animal carcass lying beside service road drain since yesterday afternoon. Terrible stench and flies everywhere.",
        "location": "Canal Bank Road near Dharampura, Lahore",
        "reporter_contact": None,
        "category": Category.SANITATION,
        "priority": Priority.NORMAL,
        "status": Status.OPEN,
        "ai_summary": "Animal carcass rotting beside service road creating foul odor.",
        "triaged_by": "rules",
        "triage_latency_ms": 112,
    },

    # Roads (5 complaints)
    {
        "seed_id": "road-01",
        "text": "Huge deep pothole formed in middle of road after monsoon rains. Cars suffering tyre bursts and suspension damage daily.",
        "location": "Main Boulevard, Gulshan-e-Ravi, Lahore",
        "reporter_contact": "0321-4567890",
        "category": Category.ROADS,
        "priority": Priority.NORMAL,
        "status": Status.IN_PROGRESS,
        "ai_summary": "Deep pothole causing vehicular damage on main boulevard.",
        "triaged_by": "rules",
        "triage_latency_ms": 100,
    },
    {
        "seed_id": "road-02",
        "text": "Road cave-in near storm drain after pipeline work. Half the road has collapsed into a trench. High danger of bus or car overturning.",
        "location": "University Road near NED Gate, Karachi",
        "reporter_contact": "0331-9876123",
        "category": Category.ROADS,
        "priority": Priority.HIGH,
        "status": Status.OPEN,
        "ai_summary": "Severe road cave-in creating collapse risk on University Road.",
        "triaged_by": "llm:groq",
        "triage_latency_ms": 290,
    },
    {
        "seed_id": "road-03",
        "text": "Illegal speed breaker constructed by residents without CDA permission. It is excessively steep and scrap car chasis.",
        "location": "Street 35, Sector F-11/2, Islamabad",
        "reporter_contact": "resident.f11@outlook.com",
        "category": Category.ROADS,
        "priority": Priority.LOW,
        "status": Status.OPEN,
        "ai_summary": "Unauthorized sharp speed breaker damaging car undercarriages.",
        "triaged_by": "rules",
        "triage_latency_ms": 110,
    },
    {
        "seed_id": "road-04",
        "text": "Missing concrete storm drain cover on side of road. Motorbikes falling in during dark hours.",
        "location": "Kohat Road near Ring Road Interchange, Peshawar",
        "reporter_contact": "0300-5544112",
        "category": Category.ROADS,
        "priority": Priority.HIGH,
        "status": Status.RESOLVED,
        "ai_summary": "Uncovered roadside storm drain causing nighttime traffic hazard.",
        "triaged_by": "rules",
        "triage_latency_ms": 135,
    },
    {
        "seed_id": "road-05",
        "text": "Gravel and construction debris dumped across left lane, obstructing traffic flow and causing traffic jam during school timings.",
        "location": "Mall Road near Charing Cross, Lahore",
        "reporter_contact": None,
        "category": Category.ROADS,
        "priority": Priority.NORMAL,
        "status": Status.OPEN,
        "ai_summary": "Construction debris blocking traffic lane during rush hours.",
        "triaged_by": "rules",
        "triage_latency_ms": 95,
    },

    # Streetlights (4 complaints)
    {
        "seed_id": "str-01",
        "text": "All streetlights completely dead on main bazaar street since 10 days. Total dark road causing mugging and snatching incidents at night.",
        "location": "Bano Bazaar, Anarkali, Lahore",
        "reporter_contact": "0300-3334445",
        "category": Category.STREETLIGHTS,
        "priority": Priority.HIGH,
        "status": Status.OPEN,
        "ai_summary": "Dark commercial street due to non-functional streetlights fostering crime.",
        "triaged_by": "rules",
        "triage_latency_ms": 105,
    },
    {
        "seed_id": "str-02",
        "text": "Streetlight pole short-circuiting with audible buzzing and sparks coming out of the base inspection panel.",
        "location": "7th Avenue near Sector G-6, Islamabad",
        "reporter_contact": "0315-6677889",
        "category": Category.STREETLIGHTS,
        "priority": Priority.HIGH,
        "status": Status.IN_PROGRESS,
        "ai_summary": "Sparking streetlight pole base inspection cover.",
        "triaged_by": "rules",
        "triage_latency_ms": 118,
    },
    {
        "seed_id": "str-03",
        "text": "Streetlight timer broken; lamps remain ON in bright daylight wasting electricity, and turn OFF at night time.",
        "location": "Lane 4, Peshawar Cantt, Peshawar",
        "reporter_contact": "0345-1122998",
        "category": Category.STREETLIGHTS,
        "priority": Priority.LOW,
        "status": Status.OPEN,
        "ai_summary": "Inverted timer keeping streetlights on in day and off at night.",
        "triaged_by": "rules",
        "triage_latency_ms": 85,
    },
    {
        "seed_id": "str-04",
        "text": "Broken lamp glass hanging from high mast streetlight. Wind might cause the heavy glass fixture to fall on pedestrians.",
        "location": "Liberty Chowk Roundabout, Lahore",
        "reporter_contact": "liberty.traders@yahoo.com",
        "category": Category.STREETLIGHTS,
        "priority": Priority.NORMAL,
        "status": Status.RESOLVED,
        "ai_summary": "Loose glass fixture hanging dangerously from mast streetlight.",
        "triaged_by": "rules",
        "triage_latency_ms": 115,
    },

    # Other (4 complaints)
    {
        "seed_id": "oth-01",
        "text": "Stray dog pack aggressive behaviour in public park. Multiple barking complaints and two children chased while cycling.",
        "location": "Jasmine Park, Sector G-10/4, Islamabad",
        "reporter_contact": "0300-7788990",
        "category": Category.OTHER,
        "priority": Priority.NORMAL,
        "status": Status.OPEN,
        "ai_summary": "Aggressive stray dog pack intimidating visitors in community park.",
        "triaged_by": "rules",
        "triage_latency_ms": 92,
    },
    {
        "seed_id": "oth-02",
        "text": "Illegal tree cutting by commercial plaza owner on municipal green belt during night hours.",
        "location": "Main Khyaban-e-Ittehad, Phase 6, DHA, Karachi",
        "reporter_contact": "savegreen.pk@gmail.com",
        "category": Category.OTHER,
        "priority": Priority.LOW,
        "status": Status.OPEN,
        "ai_summary": "Unauthorized felling of municipal green belt trees by commercial shop.",
        "triaged_by": "rules",
        "triage_latency_ms": 99,
    },
    {
        "seed_id": "oth-03",
        "text": "Noise pollution from unauthorized loud generator running 24 hours behind residential wall. Noise level unbearable for elderly patients.",
        "location": "Street 9, Cavalry Ground, Lahore Cantt",
        "reporter_contact": "0323-4455661",
        "category": Category.OTHER,
        "priority": Priority.LOW,
        "status": Status.REJECTED,
        "ai_summary": "Commercial generator operating 24/7 causing severe noise disturbance.",
        "triaged_by": "rules",
        "triage_latency_ms": 108,
    },
    {
        "seed_id": "oth-04",
        "text": "Encroachment on public footpath by vegetable and fruit vendors forcing school children to walk on busy main road traffic.",
        "location": "Liaquatabad No. 4 Super Market, Karachi",
        "reporter_contact": "0342-1234567",
        "category": Category.OTHER,
        "priority": Priority.NORMAL,
        "status": Status.OPEN,
        "ai_summary": "Footpath encroachment by street carts pushing pedestrians into traffic.",
        "triaged_by": "rules",
        "triage_latency_ms": 114,
    },
]


async def seed_database() -> None:
    from app.config import get_settings

    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    inserted_count = 0
    updated_count = 0

    async with session_factory() as session:
        async with session.begin():
            for item in SEED_COMPLAINTS:
                deterministic_id = uuid5(SEED_NAMESPACE, item["seed_id"])
                
                # Check if row already exists
                stmt = select(Complaint).where(Complaint.id == deterministic_id)
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()

                if existing is None:
                    complaint = Complaint(
                        id=deterministic_id,
                        text=item["text"],
                        location=item["location"],
                        reporter_contact=item["reporter_contact"],
                        category=item["category"],
                        priority=item["priority"],
                        status=item["status"],
                        ai_summary=item["ai_summary"],
                        triaged_by=item["triaged_by"],
                        triage_latency_ms=item["triage_latency_ms"],
                    )
                    session.add(complaint)
                    inserted_count += 1
                else:
                    # Idempotent: ensure fields match seed values
                    existing.text = item["text"]
                    existing.location = item["location"]
                    existing.reporter_contact = item["reporter_contact"]
                    existing.category = item["category"]
                    existing.priority = item["priority"]
                    existing.status = item["status"]
                    existing.ai_summary = item["ai_summary"]
                    existing.triaged_by = item["triaged_by"]
                    existing.triage_latency_ms = item["triage_latency_ms"]
                    updated_count += 1

    await engine.dispose()
    print(f"Seed completed: {inserted_count} inserted, {updated_count} existing verified/updated. Total seed records: {len(SEED_COMPLAINTS)}")


if __name__ == "__main__":
    asyncio.run(seed_database())
