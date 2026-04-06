# app/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

class BroteForm(FlaskForm):
    lugar = StringField('Lugar', validators=[DataRequired(), Length(min=1, max=100)])
    unidadnotif = StringField('Unidad Notificación', validators=[DataRequired(), Length(min=1, max=100)])
    municipio = StringField('Municipio', validators=[DataRequired(), Length(min=1, max=100)])
    diagsospecha = StringField('Diagnóstico Sospecha', validators=[DataRequired(), Length(min=1, max=100)])
    fecha_inicio = DateField('Fecha de Inicio', format='%Y-%m-%d', validators=[DataRequired()])
    fecha_alta = DateField('Fecha Alta', format='%Y-%m-%d', validators=[Optional()])
    folio = StringField('Folio', validators=[DataRequired(), Length(min=1, max=50)])

    # Validación personalizada para la fecha de inicio
    def validate_fecha_inicio(self, field):
        if self.fecha_alta.data and self.fecha_inicio.data > self.fecha_alta.data:
            raise ValidationError('La fecha de inicio no puede ser posterior a la fecha de alta.')
    
    def validate_folio(self, field):
        """Ejemplo de validación customizada para el folio"""
        if len(field.data) < 5:
            raise ValidationError('El folio debe tener al menos 5 caracteres.')
