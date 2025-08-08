document.addEventListener("DOMContentLoaded", function () {
  // Configuración de constantes
  const DATE_FIELDS = [
    { id: "fechnotifica", errorId: "error-message-fechnotifica" },
    { id: "fecha_inicio", errorId: "error-message-fechainicio" },
    { id: "fecha_ultimo_caso", errorId: "error-message-fecha_ultimo_caso" },
    { id: "fecha_alta", errorId: "error-message-fechalta" },
    { id: "fecha_consulta", errorId: "error-message-fecha_consulta" },
  ];
  const YEAR_REGEX = /^20\d{2}$/;
  const DEBOUNCE_TIME = 300;
  const FORM_IDS = ["broteForm", "form_update"]; // Soporte para múltiples formularios

  // ✅ Función para validar el formato del año
  const isValidYear = (dateStr) => {
    if (!dateStr) return false;
    const [year] = dateStr.split("-");
    return YEAR_REGEX.test(year);
  };

  // ✅ Convertir string a objeto Date (seguro)
  const parseDate = (dateStr) => {
    if (!dateStr) return null;
    const [year, month, day] = dateStr.split("-").map(Number);
    if (isNaN(year) || isNaN(month) || isNaN(day)) return null;
    return new Date(year, month - 1, day);
  };

  // ✅ Mostrar mensaje de error
  const showError = (input, errorId, message) => {
    const errorElement = document.getElementById(errorId);
    if (!errorElement || !input) return;

    errorElement.textContent = message;
    errorElement.style.display = "block";
    input.classList.add("is-invalid");
    input.classList.remove("is-valid");
  };

  // ✅ Marcar campo como válido
  const markValid = (input) => {
    if (input) {
      input.classList.remove("is-invalid");
      input.classList.add("is-valid");
    }
  };

  // ✅ Limpiar estado de validación
  const clearValidationStates = () => {
    document.querySelectorAll('[id^="error-message-"]').forEach((el) => {
      el.style.display = "none";
      el.textContent = "";
    });

    DATE_FIELDS.forEach((field) => {
      const input = document.getElementById(field.id);
      if (input) {
        input.classList.remove("is-invalid", "is-valid");
      }
    });
  };

  // ✅ Validación principal de fechas
  const validateDates = () => {
    // Obtener todos los inputs y sus valores
    const inputs = {};
    const values = {};

    DATE_FIELDS.forEach((field) => {
      inputs[field.id] = document.getElementById(field.id);
      values[field.id] = inputs[field.id]?.value;
    });

    let isValid = true;

    // Limpiar estados previos
    clearValidationStates();

    // Validar formato de año para todos los campos con valor
    DATE_FIELDS.forEach((field) => {
      if (values[field.id] && !isValidYear(values[field.id])) {
        showError(
          inputs[field.id],
          field.errorId,
          "El año debe comenzar con 20 y tener 4 dígitos."
        );
        isValid = false;
      }
    });

    // Convertir a fechas solo los campos necesarios
    const dates = {
      fechnotifica: parseDate(values.fechnotifica),
      fecha_inicio: parseDate(values.fecha_inicio),
      fecha_alta: parseDate(values.fecha_alta),
      fecha_ultimo_caso: parseDate(values.fecha_ultimo_caso),
    };

    // Validaciones lógicas entre fechas
    if (dates.fechnotifica && dates.fecha_inicio) {
      if (dates.fechnotifica < dates.fecha_inicio) {
        showError(
          inputs.fechnotifica,
          "error-message-fechnotifica",
          "La fecha de notificación no puede ser menor a la de inicio."
        );
        isValid = false;
      } else {
        markValid(inputs.fechnotifica);
      }
    }

    if (dates.fecha_ultimo_caso && dates.fecha_inicio) {
      if (dates.fecha_ultimo_caso > dates.fecha_inicio) {
        showError(
          inputs.fecha_ultimo_caso,
          "error-message-fecha_ultimo_caso",
          "La fecha del último caso no puede ser mayor a la de inicio."
        );
        isValid = false;
      } else {
        markValid(inputs.fecha_ultimo_caso);
      }
    }

    if (dates.fecha_alta && dates.fecha_inicio) {
      let errorMessage = "";

      if (dates.fecha_alta <= dates.fecha_inicio) {
        errorMessage =
          "La fecha de alta no puede ser menor o igual a la de inicio.";
      } else if (dates.fechnotifica && dates.fecha_alta <= dates.fechnotifica) {
        errorMessage =
          "La fecha de alta no puede ser menor o igual a la de notificación.";
      }

      if (errorMessage) {
        showError(inputs.fecha_alta, "error-message-fechalta", errorMessage);
        isValid = false;
      } else {
        markValid(inputs.fecha_alta);
      }
    }

    // Marcar como válidos los campos con fechas válidas
    if (values.fecha_inicio && isValidYear(values.fecha_inicio)) {
      markValid(inputs.fecha_inicio);
    }

    return isValid;
  };

  // ✅ Configurar event listeners para validación en tiempo real
  DATE_FIELDS.forEach((field) => {
    const input = document.getElementById(field.id);
    if (input) {
      input.addEventListener("input", function () {
        clearTimeout(window.validationTimeout);
        window.validationTimeout = setTimeout(validateDates, DEBOUNCE_TIME);
      });
    }
  });

validateDates();

  // ✅ Validación al enviar los formularios
  FORM_IDS.forEach((formId) => {
    const form = document.getElementById(formId);
    if (form) {
      form.addEventListener("submit", function (e) {
        if (!validateDates()) {
          e.preventDefault();
          // Desplazarse al primer error
          const firstError = document.querySelector(".is-invalid");
          if (firstError) {
            firstError.scrollIntoView({ behavior: "smooth", block: "center" });
          }
        }
      });
    }
  });
});



