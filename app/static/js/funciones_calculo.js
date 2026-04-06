/*Funcion mostrar INPUT LUGAR*/
document.addEventListener("DOMContentLoaded", function () {
    var select = document.getElementById("evento");
    var inputLugar = document.getElementById("lugar");

    function verificarEvento() {
        // Si el valor del select es vacío, deshabilitar el input lugar
        if (select.value === "" || select.value === "BROTE ESCOLAR" || select.value === "BROTE LOCALIZADO") {
            inputLugar.disabled = false;  // Deshabilitar el input lugar
            inputLugar.value = inputLugar.getAttribute('data-flask-value') || '';
            //inputLugar.value = "";
        //} else if (select.value === "BROTE ESCOLAR" || select.value === "BROTE LOCALIZADO") {
        //    inputLugar.disabled = false;
        //    inputLugar.value = "";
        } else {
            inputLugar.disabled = true;
            document.getElementById('lugar').value = 'NO APLICA';
        }
    }

    // Evento cuando cambia la selección
    select.addEventListener("change", function () {
        verificarEvento();
    });

    // Detectar Tab y Enter en el select
    select.addEventListener("keydown", function (e) {
        if (e.key === "Tab" || e.key === "Enter") {
            verificarEvento();
            setTimeout(() => {
                if (!inputLugar.disabled) {
                    inputLugar.focus();
                }
            }, 50);
        }
    });

    verificarEvento();

});




/**Sugerencias de localidad*/
document.addEventListener("DOMContentLoaded", function () {
    function manejarSugerencias(inputId, datalistId, storageKey) {
        const input = document.getElementById(inputId);
        const datalist = document.getElementById(datalistId);

        // Cargar valores almacenados
        function cargarSugerencias() {
            const valores = JSON.parse(localStorage.getItem(storageKey)) || [];
            datalist.innerHTML = ""; // Limpiar opciones previas

            valores.forEach(valor => {
                const option = document.createElement("option");
                option.value = valor;
                datalist.appendChild(option);
            });
        }

        // Guardar nuevo valor
        input.addEventListener("change", function () {
            let valores = JSON.parse(localStorage.getItem(storageKey)) || [];
            const nuevoValor = input.value.trim();

            if (nuevoValor && !valores.includes(nuevoValor)) {
                valores.push(nuevoValor);
                localStorage.setItem(storageKey, JSON.stringify(valores));
            }
        });

        // Cargar sugerencias al inicio
        cargarSugerencias();
    }

    // Integrar para Localidad y Unidad
    manejarSugerencias("localidad", "sugerencias-localidad", "localidades");
    manejarSugerencias("unidad", "sugerencias-unidad", "unidades");
});



//Validar datalist
document.addEventListener("DOMContentLoaded", function () {
    // Lista de campos que quieres validar
    const campos = [
        { inputId: "evento", datalistId: "datalist_tipoevento", errorId: "error-evento" },
        { inputId: "institucion", datalistId: "datalist_institucion", errorId: "error-institucion" },
        { inputId: "municipio", datalistId: "datalist_municipios", errorId: "error-municipio" },
        { inputId: "juris", datalistId: "datalist_jurisdicciones", errorId: "error-jurisdicciones" },
        { inputId: "diagsospecha", datalistId: "datalist_diagsospecha", errorId: "error-diagsospecha" }
    ];

    campos.forEach(({ inputId, datalistId, errorId }) => {
        const input = document.getElementById(inputId);
        const datalist = document.getElementById(datalistId);
        const errorDiv = document.getElementById(errorId);

        if (input && datalist && errorDiv) {
            input.addEventListener("blur", function () {
                const valor = input.value.trim();
                let valido = false;

                for (let option of datalist.options) {
                    if (option.value === valor) {
                        valido = true;
                        break;
                    }
                }

                if (!valido) {
                    errorDiv.textContent = "Seleccione un valor válido de la lista.";
                    errorDiv.style.display = "block";
                    input.classList.add("is-invalid");
                    input.classList.remove("is-valid");
                    input.focus();
                } else {
                    errorDiv.textContent = "";
                    errorDiv.style.display = "none";
                    input.classList.remove("is-invalid");
                    input.classList.add("is-valid");
                }
            });
        }
    });
});





// Configuración de constantes
const CALCULATION_ENDPOINTS = {
    SUM: '/brotes/sumar',
    ATTACK_RATE: '/brotes/ataque'
};

const INPUT_IDS = {
    MALE: 'pobmascexpuesta',
    FEMALE: 'pobfemexpuesta',
    PROBABLES: 'probables',
    TOTAL: 'total',
    ATTACK_RATE: 'ataque'
};

// Función para obtener valor numérico de un input
const getNumericValue = (elementId) => {
    const element = document.getElementById(elementId);
    if (!element) return 0;
    return element.value ? parseInt(element.value) : 0;
};

// Función genérica para realizar peticiones fetch
const fetchCalculation = async (endpoint, data) => {
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`Error in ${endpoint} calculation:`, error);
        return { error: error.message };
    }
};

// Función para realizar la suma
const calculateSum = async () => {
    const data = {
        pobMasculino: getNumericValue(INPUT_IDS.MALE),
        pobFemenino: getNumericValue(INPUT_IDS.FEMALE)
    };

    const result = await fetchCalculation(CALCULATION_ENDPOINTS.SUM, data);
    
    const totalElement = document.getElementById(INPUT_IDS.TOTAL);
    if (totalElement) {
        totalElement.value = result.error ? "Error" : result.resultado;
    }
};

// Función para calcular la tasa de ataque
const calculateAttackRate = async () => {
    const data = {
        pobMasculino: getNumericValue(INPUT_IDS.MALE),
        pobFemenino: getNumericValue(INPUT_IDS.FEMALE),
        probables: getNumericValue(INPUT_IDS.PROBABLES)
    };

    const result = await fetchCalculation(CALCULATION_ENDPOINTS.ATTACK_RATE, data);
    
    const attackRateElement = document.getElementById(INPUT_IDS.ATTACK_RATE);
    if (attackRateElement) {
        attackRateElement.value = result.error ? "Error" : result.resultado.toFixed(1);
    }
};

// Ejecutar cálculos iniciales si hay valores existentes
const runInitialCalculations = () => {
    const maleValue = getNumericValue(INPUT_IDS.MALE);
    const femaleValue = getNumericValue(INPUT_IDS.FEMALE);
    const probablesValue = getNumericValue(INPUT_IDS.PROBABLES);

    // Solo calcular si hay valores existentes
    if (maleValue > 0 || femaleValue > 0) {
        calculateSum();
    }
    
    if ((maleValue > 0 || femaleValue > 0) && probablesValue > 0) {
        calculateAttackRate();
    }
};

// Configurar event listeners
const setupEventListeners = () => {
    // Elementos que afectan ambos cálculos
    const commonInputs = [
        document.getElementById(INPUT_IDS.MALE),
        document.getElementById(INPUT_IDS.FEMALE)
    ];

    // Configurar listeners para inputs comunes
    commonInputs.forEach(input => {
        if (input) {
            input.addEventListener('input', () => {
                calculateSum();
                calculateAttackRate();
            });
        }
    });

    // Configurar listener específico para probables
    const probablesInput = document.getElementById(INPUT_IDS.PROBABLES);
    if (probablesInput) {
        probablesInput.addEventListener('input', calculateAttackRate);
    }
};

// Inicialización completa
const initializeCalculations = () => {
    setupEventListeners();
    runInitialCalculations(); // Ejecutar cálculos iniciales para edit.html
};

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initializeCalculations);