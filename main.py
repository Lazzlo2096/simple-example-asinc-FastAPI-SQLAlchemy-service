from fastapi import FastAPI, HTTPException

from sqlalchemy import Column, Integer, String, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from pydantic_sqlalchemy import sqlalchemy_to_pydantic

app = FastAPI()

# Подключение к базе данных PostgreSQL
your_username = "postgres"
your_password = "postgres"
end_point     = "localhost"
db_name       = "db_name"
DATABASE_URL = f'postgresql+asyncpg://{your_username}:{your_password}@{end_point}/{db_name}'

engine = create_async_engine(DATABASE_URL)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)

ItemModel = sqlalchemy_to_pydantic(Item, exclude=['id'])

@app.on_event("startup")
async def init_tables():
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)

async def get_item(item_id: int, session: AsyncSession):
    statement = select(Item).where(Item.id == item_id)
    result = await session.execute(statement)
    db_item = result.scalar_one_or_none()
    
    if db_item:
        return ItemModel.from_orm(db_item)
    
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items/", response_model=ItemModel)
async def create_item(item: ItemModel):
    async with Session() as session:
        async with session.begin():
            db_item = Item(**item.dict())
            session.add(db_item)
            await session.flush()
            await session.refresh(db_item)
            return await get_item(db_item.id, session=session)
