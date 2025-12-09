-- Crear la base de datos
CREATE DATABASE IF NOT EXISTS brotes_app
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE brotes_app;

-- 1. Tabla tipoeventos (1:N con brotes)
CREATE TABLE tipoeventos (
  idtipoevento INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  PRIMARY KEY (idtipoevento),
  UNIQUE KEY (nombre)
) ENGINE=InnoDB;

-- 2. Tabla instituciones (1:N con unidad_notificante)
CREATE TABLE instituciones (
  idinstitucion INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  PRIMARY KEY (idinstitucion),
  UNIQUE KEY (nombre)
) ENGINE=InnoDB;

-- 3. Tabla jurisdicciones (1:N con municipios)
CREATE TABLE jurisdicciones (
  idjurisdiccion INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  PRIMARY KEY (idjurisdiccion),
  UNIQUE KEY (nombre)
) ENGINE=InnoDB;

-- 4. Tabla municipios (1:N con unidad_notificante)
CREATE TABLE municipios (
  idmunicipio INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  idjurisdiccion INT NOT NULL,
  PRIMARY KEY (idmunicipio),
  UNIQUE KEY (nombre),
  CONSTRAINT fk_municipios_jurisdicciones
    FOREIGN KEY (idjurisdiccion)
    REFERENCES jurisdicciones (idjurisdiccion)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 5. Tabla unidad_notificante (1:N con brotes)
CREATE TABLE unidad_notificante (
  idunidad INT NOT NULL AUTO_INCREMENT,
  idinstitucion INT NOT NULL,
  unidadnotif VARCHAR(150) NULL,
  domicilio VARCHAR(255) NULL,
  localidad VARCHAR(100) NULL,
  idmunicipio INT NOT NULL,
  PRIMARY KEY (idunidad),
  CONSTRAINT fk_unidad_institucion
    FOREIGN KEY (idinstitucion)
    REFERENCES instituciones (idinstitucion)
    ON DELETE RESTRICT,
  CONSTRAINT fk_unidad_municipio
    FOREIGN KEY (idmunicipio)
    REFERENCES municipios (idmunicipio)
    ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 6. Tabla brotes (1:1 con antecedentes, 1:N con documentos)
CREATE TABLE brotes (
  idbrote INT NOT NULL AUTO_INCREMENT,
  lugar VARCHAR(150) NULL,
  idunidad INT NOT NULL,
  tipoeventos_idtipoevento INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (idbrote),
  CONSTRAINT fk_brotes_unidad
    FOREIGN KEY (idunidad)
    REFERENCES unidad_notificante (idunidad)
    ON DELETE RESTRICT,
  CONSTRAINT fk_brotes_tipoeventos
    FOREIGN KEY (tipoeventos_idtipoevento)
    REFERENCES tipoeventos (idtipoevento)
    ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 7. Tabla diagnosticos (1:N con antecedentes)
CREATE TABLE diagnosticos (
  iddiag INT NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(150) NOT NULL,
  PRIMARY KEY (iddiag),
  UNIQUE KEY (nombre)
) ENGINE=InnoDB;

-- 8. Tabla antecedentes (1:1 con brotes)
CREATE TABLE antecedentes (
  idantecedente INT NOT NULL AUTO_INCREMENT,
  iddiag INT NOT NULL,
  brote_id INT NOT NULL,
  fechnotifica DATE NULL,
  fechinicio DATE NULL,
  casosprob INT DEFAULT 0,
  casosconf INT DEFAULT 0,
  defunciones INT DEFAULT 0,
  fechaultimocaso DATE NULL,
  resultado VARCHAR(100) NULL,
  fechalta DATE NULL,
  observaciones TEXT NULL,
  pobmascexp INT DEFAULT 0,
  pobfemexp INT DEFAULT 0,
  PRIMARY KEY (idantecedente),
  UNIQUE KEY (brote_id), -- Cada brote solo puede tener un antecedente
  CONSTRAINT fk_antecedentes_diag
    FOREIGN KEY (iddiag)
    REFERENCES diagnosticos (iddiag)
    ON DELETE CASCADE,
  CONSTRAINT fk_antecedentes_brote
    FOREIGN KEY (brote_id)
    REFERENCES brotes (idbrote)
    ON DELETE CASCADE
) ENGINE=InnoDB;

-- 9. Tabla documentos (1:N con brotes)
CREATE TABLE documentos (
  iddocumento INT NOT NULL AUTO_INCREMENT,
  brote_id INT NOT NULL,
  nombre_archivo VARCHAR(255) NULL,
  path VARCHAR(255) NULL,
  tipo_notificacion ENUM('INICIAL', 'SEGUIMIENTO', 'FINAL', 'NOTA') NOT NULL,
  folionotinmed VARCHAR(100) NULL,
  fechnotinmed DATE NULL,
  fechacarga DATETIME DEFAULT CURRENT_TIMESTAMP,
  fechmodificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (iddocumento),
  CONSTRAINT fk_documentos_brote
    FOREIGN KEY (brote_id)
    REFERENCES brotes (idbrote)
    ON DELETE CASCADE
) ENGINE=InnoDB;
