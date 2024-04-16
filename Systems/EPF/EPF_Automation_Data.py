import logging

from sqlalchemy import Column, Integer, String, JSON, select, func
from sqlalchemy.exc import InterfaceError
from sqlalchemy.orm import declarative_base

from Backend.Database.engine import look_up_engine, lookup_session

Base = declarative_base()


class Automation_Data(Base):
    __tablename__ = "EPF_Complex_Data"
    # ID Columns
    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String())
    display_name = Column(String(), unique=True)
    category = Column(String())
    traits = Column(String())
    level = Column(Integer())
    data = Column(JSON())


async def upload_data(data):
    await create_data_table()
    await load_complex_data(data)


async def create_data_table():
    async with look_up_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def load_complex_data(data: dict):
    async_session = lookup_session
    for key in data.keys():
        # print(key)
        async with async_session() as session:
            query = await session.execute((select(Automation_Data).where(Automation_Data.name == key.lower())))
            entry = query.scalars().all()
        if len(entry) > 0:
            if type(data[key]) == list:
                for x in data[key]:
                    try:
                        async with async_session() as session:
                            query = await session.execute(
                                select(Automation_Data)
                                .where(func.lower(Automation_Data.name) == key.lower())
                                .where(func.lower(Automation_Data.display_name) == x["title"].lower())
                            )
                            entry = query.scalars().one()

                            entry.name = key.lower()
                            entry.display_name = x["title"]
                            entry.category = x["category"]
                            entry.traits = ", ".join(x["traits"])
                            entry.level = x["lvl"]
                            entry.data = x

                            await session.commit()
                    except Exception:
                        async with async_session() as session:
                            async with session.begin():
                                new_entry = Automation_Data(
                                    name=key.lower(),
                                    display_name=x["title"],
                                    category=x["category"],
                                    traits=", ".join(x["traits"]),
                                    level=x["lvl"],
                                    data=x,
                                )
                                session.add(new_entry)
                            await session.commit()

            else:
                async with async_session() as session:
                    query = await session.execute(
                        select(Automation_Data).where(func.lower(Automation_Data.name) == key.lower())
                    )
                    entry = query.scalars().one()

                    entry.name = key.lower()
                    entry.display_name = data[key]["title"]
                    entry.category = data[key]["category"]
                    entry.traits = ", ".join(data[key]["traits"])
                    entry.level = data[key]["lvl"]
                    entry.data = data[key]

                    await session.commit()
        else:
            if type(data[key]) == list:
                for x in data[key]:
                    async with async_session() as session:
                        async with session.begin():
                            new_entry = Automation_Data(
                                name=key.lower(),
                                display_name=x["title"],
                                category=x["category"],
                                traits=", ".join(x["traits"]),
                                level=x["lvl"],
                                data=x,
                            )
                            session.add(new_entry)
                        await session.commit()
            else:
                async with async_session() as session:
                    async with session.begin():
                        new_entry = Automation_Data(
                            name=key.lower(),
                            display_name=data[key]["title"],
                            category=data[key]["category"],
                            traits=", ".join(data[key]["traits"]),
                            level=data[key]["lvl"],
                            data=data[key],
                        )
                        session.add(new_entry)
                    await session.commit()


async def EPF_retreive_complex_data(search: str):
    try:
        async with lookup_session() as session:
            query = await session.execute(
                select(Automation_Data).where(func.lower(Automation_Data.name) == search.lower())
            )
            return query.scalars().all()
    except InterfaceError as e:
        logging.error(f"Lookup Database was unexpectedly closed. {e}")

        async with lookup_session() as session:
            query = await session.execute(
                select(Automation_Data).where(func.lower(Automation_Data.name) == search.lower())
            )
            return query.scalars().all()
