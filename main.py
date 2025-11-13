from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select
import os

# --- 1. Definición de Modelos (Tablas de la Base de Datos) y Modelos de Actualización ---

# Campo de ID autoincremental
ID_FIELD = Field(
    default=None, 
    primary_key=True, 
    sa_column_kwargs={"autoincrement": True}
)

class Heroe(SQLModel, table=True):
    """Modelo principal para la tabla de Héroes."""
    id: Optional[int] = ID_FIELD
    nombre: str = Field(index=True)
    edad: Optional[int] = Field(default=None, index=True)
    nombre_secreto: str
    poder: Optional[str] = None 

# Modelo para actualizar (PATCH) - hace que todos los campos sean opcionales
class HeroeUpdate(SQLModel):
    nombre: Optional[str] = None
    edad: Optional[int] = None
    nombre_secreto: Optional[str] = None
    poder: Optional[str] = None


class Equipo(SQLModel, table=True):
    """Modelo principal para la tabla de Equipos."""
    id: Optional[int] = ID_FIELD
    nombre_equipo: str = Field(index=True)
    base_operaciones: str
    fundacion_anio: int

class EquipoUpdate(SQLModel):
    nombre_equipo: Optional[str] = None
    base_operaciones: Optional[str] = None
    fundacion_anio: Optional[int] = None


class Villano(SQLModel, table=True):
    """Modelo principal para la tabla de Villanos."""
    id: Optional[int] = ID_FIELD
    nombre_villano: str = Field(index=True)
    amenaza_nivel: int 
    ultima_ubicacion: Optional[str] = None

class VillanoUpdate(SQLModel):
    nombre_villano: Optional[str] = None
    amenaza_nivel: Optional[int] = None
    ultima_ubicacion: Optional[str] = None


# --- 2. Configuración y Conexión de la Base de Datos (Sin cambios) ---


DATABASE_URL = os.environ.get("DATABASE_URL") 

if not DATABASE_URL:
    # Esto solo correría si la variable no está seteada, es una buena práctica forzarla.
    # En Render, esta variable siempre estará seteada.
    raise Exception("La variable de entorno DATABASE_URL no está configurada.")

# La conexión de PostgreSQL no necesita el argumento check_same_thread
motor_db = create_engine(DATABASE_URL)


def crear_db_y_tablas():
    """Crea la base de datos y todas las tablas definidas."""
    # Nota: SQLModel.metadata.create_all(motor_db) seguirá funcionando
    # con PostgreSQL una vez que la conexión sea correcta.
    SQLModel.metadata.create_all(motor_db)

def obtener_sesion():
    with Session(motor_db) as sesion:
        yield sesion

SesionDep = Annotated[Session, Depends(obtener_sesion)]


# --- 3. Inicialización de la Aplicación FastAPI (Sin cambios) ---

app = FastAPI(title="API CRUD de Héroes, Equipos y Villanos")

@app.on_event("startup")
def al_iniciar():
    crear_db_y_tablas()


# --- 4. Endpoints CRUD para Héroes (Heroe) ---

# C: Crear (POST)
@app.post("/heroes/", response_model=Heroe)
def crear_heroe(heroe: Heroe, sesion: SesionDep) -> Heroe:
    sesion.add(heroe)
    sesion.commit()
    sesion.refresh(heroe)
    return heroe

# R: Leer Lista (GET)
@app.get("/heroes/", response_model=list[Heroe])
def leer_heroes(
    sesion: SesionDep,
    desplazamiento: int = 0,
    limite: Annotated[int, Query(le=100)] = 100,
) -> list[Heroe]:
    heroes = sesion.exec(select(Heroe).offset(desplazamiento).limit(limite)).all()
    return heroes

# R: Leer por ID (GET)
@app.get("/heroes/{heroe_id}", response_model=Heroe)
def leer_heroe(heroe_id: int, sesion: SesionDep) -> Heroe:
    heroe = sesion.get(Heroe, heroe_id)
    if not heroe:
        raise HTTPException(status_code=404, detail="Héroe no encontrado")
    return heroe

# U: Actualizar (PATCH)
@app.patch("/heroes/{heroe_id}", response_model=Heroe)
def actualizar_heroe(heroe_id: int, heroe: HeroeUpdate, sesion: SesionDep) -> Heroe:
    db_heroe = sesion.get(Heroe, heroe_id)
    if not db_heroe:
        raise HTTPException(status_code=404, detail="Héroe no encontrado")
    
    # Copia los datos nuevos sobre el objeto existente, ignorando los campos 'None'
    heroe_datos = heroe.model_dump(exclude_unset=True)
    db_heroe.model_validate(db_heroe, update=heroe_datos)
    
    sesion.add(db_heroe)
    sesion.commit()
    sesion.refresh(db_heroe)
    return db_heroe

# D: Eliminar (DELETE)
@app.delete("/heroes/{heroe_id}")
def eliminar_heroe(heroe_id: int, sesion: SesionDep):
    heroe = sesion.get(Heroe, heroe_id)
    if not heroe:
        raise HTTPException(status_code=404, detail="Héroe no encontrado")
    sesion.delete(heroe)
    sesion.commit()
    return {"ok": True}


# --- 5. Endpoints CRUD para Equipos (Equipo) ---

# C: Crear (POST)
@app.post("/equipos/", response_model=Equipo)
def crear_equipo(equipo: Equipo, sesion: SesionDep) -> Equipo:
    sesion.add(equipo)
    sesion.commit()
    sesion.refresh(equipo)
    return equipo

# R: Leer Lista (GET)
@app.get("/equipos/", response_model=list[Equipo])
def leer_equipos(sesion: SesionDep) -> list[Equipo]:
    equipos = sesion.exec(select(Equipo)).all()
    return equipos

# U: Actualizar (PATCH)
@app.patch("/equipos/{equipo_id}", response_model=Equipo)
def actualizar_equipo(equipo_id: int, equipo: EquipoUpdate, sesion: SesionDep) -> Equipo:
    db_equipo = sesion.get(Equipo, equipo_id)
    if not db_equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    equipo_datos = equipo.model_dump(exclude_unset=True)
    db_equipo.model_validate(db_equipo, update=equipo_datos)
    
    sesion.add(db_equipo)
    sesion.commit()
    sesion.refresh(db_equipo)
    return db_equipo

# D: Eliminar (DELETE)
@app.delete("/equipos/{equipo_id}")
def eliminar_equipo(equipo_id: int, sesion: SesionDep):
    equipo = sesion.get(Equipo, equipo_id)
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    sesion.delete(equipo)
    sesion.commit()
    return {"ok": True}


# --- 6. Endpoints CRUD para Villanos (Villano) ---

# C: Crear (POST)
@app.post("/villanos/", response_model=Villano)
def crear_villano(villano: Villano, sesion: SesionDep) -> Villano:
    sesion.add(villano)
    sesion.commit()
    sesion.refresh(villano)
    return villano

# R: Leer Lista (GET)
@app.get("/villanos/", response_model=list[Villano])
def leer_villanos(sesion: SesionDep) -> list[Villano]:
    villanos = sesion.exec(select(Villano)).all()
    return villanos

# U: Actualizar (PATCH)
@app.patch("/villanos/{villano_id}", response_model=Villano)
def actualizar_villano(villano_id: int, villano: VillanoUpdate, sesion: SesionDep) -> Villano:
    db_villano = sesion.get(Villano, villano_id)
    if not db_villano:
        raise HTTPException(status_code=404, detail="Villano no encontrado")
    
    villano_datos = villano.model_dump(exclude_unset=True)
    db_villano.model_validate(db_villano, update=villano_datos)
    
    sesion.add(db_villano)
    sesion.commit()
    sesion.refresh(db_villano)
    return db_villano

# D: Eliminar (DELETE)
@app.delete("/villanos/{villano_id}")
def eliminar_villano(villano_id: int, sesion: SesionDep):
    villano = sesion.get(Villano, villano_id)
    if not villano:
        raise HTTPException(status_code=404, detail="Villano no encontrado")
    sesion.delete(villano)
    sesion.commit()
    return {"ok": True}