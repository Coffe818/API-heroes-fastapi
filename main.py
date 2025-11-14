from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security.api_key import APIKeyHeader # Necesaria para la seguridad
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy.engine.base import Engine  # Necesario Engine
import os

# --- 1. Definición de Modelos (Sin Cambios) ---
ID_FIELD = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})

class Heroe(SQLModel, table=True):
    id: Optional[int] = ID_FIELD
    nombre: str = Field(index=True)
    edad: Optional[int] = Field(default=None, index=True)
    nombre_secreto: str
    poder: Optional[str] = None
class HeroeUpdate(SQLModel):
    nombre: Optional[str] = None
    edad: Optional[int] = None
    nombre_secreto: Optional[str] = None
    poder: Optional[str] = None
class Equipo(SQLModel, table=True):
    id: Optional[int] = ID_FIELD
    nombre_equipo: str = Field(index=True)
    base_operaciones: str
    fundacion_anio: int
class EquipoUpdate(SQLModel):
    nombre_equipo: Optional[str] = None
    base_operaciones: Optional[str] = None
    fundacion_anio: Optional[int] = None
class Villano(SQLModel, table=True):
    id: Optional[int] = ID_FIELD
    nombre_villano: str = Field(index=True)
    amenaza_nivel: int
    ultima_ubicacion: Optional[str] = None
class VillanoUpdate(SQLModel):
    nombre_villano: Optional[str] = None
    amenaza_nivel: Optional[int] = None
    ultima_ubicacion: Optional[str] = None

# --- 2. CONFIGURACIÓN DE LA BASE DE DATOS Y CONEXIÓN DIFERIDA ---

## Variables de entorno
DATABASE_URL = os.environ.get("DATABASE_URL")
API_CLAVE_SECRETA = os.environ.get("API_CLAVE_SECRETA")

# 1. Validación de la URL: Si no está en el entorno (Render/Docker), fallamos inmediatamente.
if not DATABASE_URL:
    raise Exception("La variable de entorno DATABASE_URL no está configurada.")

# 2. Variable global para el motor (Inicialmente None, se llena en el startup)
motor_db: Engine | None = None


def crear_db_y_tablas():
    """Crea la base de datos y todas las tablas definidas."""
    if motor_db is None:
        raise Exception("El motor de la base de datos no se ha inicializado correctamente.")
    SQLModel.metadata.create_all(motor_db)


def obtener_sesion():
    if motor_db is None:
        raise Exception("El motor de la base de datos no se ha inicializado.")
    with Session(motor_db) as sesion:
        yield sesion


SesionDep = Annotated[Session, Depends(obtener_sesion)]

# --- 2.1 Configuración de Autenticación (Dependencia) ---

api_key_header_auth = APIKeyHeader(name="X-API-Key", auto_error=False)


def verificar_acceso(api_key: str = Depends(api_key_header_auth)):
    """Verifica si la clave enviada por el cliente coincide con la clave secreta."""
    if api_key is None or api_key != API_CLAVE_SECRETA:
        raise HTTPException(
            status_code=401, detail="Acceso Denegado: Clave API inválida o faltante."
        )
    return True

# 1. Creamos el objeto Depends() para la inicialización global
DEPENDENCIA_GLOBAL_SEGURA = Depends(verificar_acceso)

# --- 3. Inicialización de la Aplicación FastAPI (Con Dependencias Globales) ---

app = FastAPI(
    title="API CRUD de Héroes, Equipos y Villanos",
    dependencies=[DEPENDENCIA_GLOBAL_SEGURA] # <--- ¡APLICACIÓN GLOBAL DE SEGURIDAD!
)


@app.on_event("startup")
def al_iniciar():
    """Crea el motor de la DB y las tablas cuando la aplicación está lista."""
    global motor_db
    
    # 🚨 FIX: La conexión se crea aquí, después de que la red de Docker esté lista.
    motor_db = create_engine(DATABASE_URL) 
    crear_db_y_tablas() # Crea todas las tablas en la nueva DB


# --- 4. Endpoints CRUD para Héroes (Heroe) ---
# Todos requieren seguridad gracias a la configuración global

@app.post("/heroes/", response_model=Heroe)
def crear_heroe(heroe: Heroe, sesion: SesionDep) -> Heroe:
    sesion.add(heroe)
    sesion.commit()
    sesion.refresh(heroe)
    return heroe

@app.get("/heroes/", response_model=list[Heroe])
def leer_heroes(
    sesion: SesionDep,
    desplazamiento: int = 0,
    limite: Annotated[int, Query(le=100)] = 100,
) -> list[Heroe]:
    heroes = sesion.exec(select(Heroe).offset(desplazamiento).limit(limite)).all()
    return heroes

@app.get("/heroes/{heroe_id}", response_model=Heroe)
def leer_heroe(heroe_id: int, sesion: SesionDep) -> Heroe:
    heroe = sesion.get(Heroe, heroe_id)
    if not heroe:
        raise HTTPException(status_code=404, detail="Héroe no encontrado")
    return heroe

@app.patch("/heroes/{heroe_id}", response_model=Heroe)
def actualizar_heroe(heroe_id: int, heroe: HeroeUpdate, sesion: SesionDep) -> Heroe:
    db_heroe = sesion.get(Heroe, heroe_id)
    if not db_heroe:
        raise HTTPException(status_code=404, detail="Héroe no encontrado")

    heroe_datos = heroe.model_dump(exclude_unset=True)
    db_heroe.model_validate(db_heroe, update=heroe_datos)

    sesion.add(db_heroe)
    sesion.commit()
    sesion.refresh(db_heroe)
    return db_heroe

@app.delete("/heroes/{heroe_id}")
def eliminar_heroe(heroe_id: int, sesion: SesionDep):
    heroe = sesion.get(Heroe, heroe_id)
    if not heroe:
        raise HTTPException(status_code=404, detail="Héroe no encontrado")
    sesion.delete(heroe)
    sesion.commit()
    return {"ok": True}


# --- 5. Endpoints CRUD para Equipos (Equipo) ---
# ... (Los demás endpoints siguen el mismo patrón limpio) ...

@app.post("/equipos/", response_model=Equipo)
def crear_equipo(equipo: Equipo, sesion: SesionDep) -> Equipo:
    sesion.add(equipo)
    sesion.commit()
    sesion.refresh(equipo)
    return equipo

@app.get("/equipos/", response_model=list[Equipo])
def leer_equipos(sesion: SesionDep) -> list[Equipo]:
    equipos = sesion.exec(select(Equipo)).all()
    return equipos

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

@app.delete("/equipos/{equipo_id}")
def eliminar_equipo(equipo_id: int, sesion: SesionDep):
    equipo = sesion.get(Equipo, equipo_id)
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    sesion.delete(equipo)
    sesion.commit()
    return {"ok": True}


# --- 6. Endpoints CRUD para Villanos (Villano) ---

@app.post("/villanos/", response_model=Villano)
def crear_villano(villano: Villano, sesion: SesionDep) -> Villano:
    sesion.add(villano)
    sesion.commit()
    sesion.refresh(villano)
    return villano

@app.get("/villanos/", response_model=list[Villano])
def leer_villanos(sesion: SesionDep) -> list[Villano]:
    villanos = sesion.exec(select(Villano)).all()
    return villanos

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

@app.delete("/villanos/{villano_id}")
def eliminar_villano(villano_id: int, sesion: SesionDep):
    villano = sesion.get(Villano, villano_id)
    if not villano:
        raise HTTPException(status_code=404, detail="Villano no encontrado")
    sesion.delete(villano)
    sesion.commit()
    return {"ok": True}