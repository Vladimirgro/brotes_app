document.addEventListener("DOMContentLoaded", function () {

    window.map = new maplibregl.Map({
        container: 'map',
        style: 'https://demotiles.maplibre.org/style.json',
        center: [-98.8, 20.5],
        zoom: 8
    });

    map.addControl(new maplibregl.NavigationControl());

    let municipiosData = null;    
    let estadoBBox = null;
    let jurisdiccionesGeoJSON = null;

    map.on('load', async function () {

        try {
            const response = await fetch('/gis/api/unidades');
            const data = await response.json();

            
            map.addSource('unidades', {
                type: 'geojson',
                data: data
            });            
            

            map.addLayer({
                id: 'unidades-layer',
                type: 'symbol',
                source: 'unidades',
                layout: {
                    'icon-image': [
                        'match',
                        ['get', 'institucion'],

                        'INSTITUTO MEXICANO DEL SEGURO SOCIAL', 'imss-icon',
                        'SERVICIOS DE SALUD IMSS BIENESTAR', 'imss-bienestar-icon',
                        'CRUZ ROJA MEXICANA', 'cruz-roja-icon',

                        'default-icon' // por defecto
                    ],
                    'icon-size': 0.8,
                    'icon-allow-overlap': true
                }
                // paint: {
                //     'circle-radius': 6,
                //     'circle-stroke-width': 1,
                //     'circle-stroke-color': '#ffffff',
                //     'circle-color': [
                //         'match',
                //         ['get', 'institucion'],
                //         "SECRETARIA DE SALUD", '#1f77b4',
                //         "SERVICIOS DE SALUD IMSS BIENESTAR", '#2ca02c',
                //         "INSTITUTO MEXICANO DEL SEGURO SOCIAL", '#ff7f0e',
                //         "INSTITUTO MEXICANO DEL SEGURO SOCIAL REGIMEN BIENESTAR", 'imss-bienestar-icon',
                //         "INSTITUTO DE SEGURIDAD Y SERVICIOS SOCIALES DE LOS TRABAJADORES DEL ESTADO", '#1f77b4',
                //         "SISTEMA NACIONAL PARA EL DESARROLLO INTEGRAL DE LA FAMILIA", '#11e6d4',
                //         "CRUZ ROJA MEXICANA", '#a31fb4',
                //         "PETROLEOS MEXICANOS", '#1f77b4',                      
                //         '#6c757d' // color por defecto
                //     ]
                // }
            });           

            map.on('click', 'unidades-layer', function (e) {
                const props = e.features[0].properties;

                new maplibregl.Popup()
                    .setLngLat(e.lngLat)
                    .setHTML(`
                        <strong>${props.nombre}</strong><br>
                        <b>CLUES:</b> ${props.clues}<br>
                        <b>Institución:</b> ${props.institucion}<br>
                        <b>Nivel:</b> ${props.nivel_atencion}<br>
                        <b>Municipio:</b> ${props.municipio}<br>
                        <b>Jurisdicción:</b> ${props.jurisdiccion}
                    `)
                    .addTo(map);
            });


            map.loadImage('/static/gis/icons/imss_bienestar.png', (error, image) => {
                if (!error && !map.hasImage('imss-bienestar-icon')) {
                    map.addImage('imss-bienestar-icon', image);
                }
            });

            const responseMun = await fetch('/static/gis/data/municipios.geojson');
            municipiosData = await responseMun.json();

            map.addSource('municipios', {
                type: 'geojson',
                data: municipiosData
            });

            map.addLayer({
                id: 'municipios-line',
                type: 'line',
                source: 'municipios',
                paint: {
                    'line-color': '#000',
                    'line-width': 1
                }
            });

            map.addLayer({
                id: 'municipios-fill',
                type: 'fill',
                source: 'municipios',
                paint: {
                    'fill-color': '#5180e6', // azul suave
                    'fill-opacity': 0 // inicia invisible
                }
            }, 'municipios-line');

            // Calcular bbox del estado completo
            estadoBBox = turf.bbox(municipiosData);


            const responseJur = await fetch('/gis/api/jurisdicciones');
            const datosJur = await responseJur.json();

            const jurisdiccionesMap = {};

            datosJur.forEach(item => {
                if (!jurisdiccionesMap[item.jurisdiccion]) {
                    jurisdiccionesMap[item.jurisdiccion] = [];
                }
                jurisdiccionesMap[item.jurisdiccion].push(item.municipio);
            });

            

            // ===============================
            // 🔥 Poblar select de jurisdicciones
            // ===============================

            const selectJur = document.getElementById('filtroJurisdiccion');

            Object.keys(jurisdiccionesMap).forEach(nombreJur => {
                const option = document.createElement('option');
                option.value = nombreJur;
                option.textContent = nombreJur;
                selectJur.appendChild(option);
            });

            // ===============================
            // 3️⃣ Crear MultiPolygon estable
            // ===============================

            const jurisdiccionesFeatures = [];

            for (const [nombreJur, listaMunicipios] of Object.entries(jurisdiccionesMap)) {

                const municipiosFiltrados = municipiosData.features.filter(f =>
                    listaMunicipios.some(m =>
                        m.trim().toUpperCase() ===
                        f.properties.NOMGEO.trim().toUpperCase()
                    )
                );

                if (municipiosFiltrados.length === 0) continue;

                const multiPolygonCoords = [];

                municipiosFiltrados.forEach(feature => {

                    if (feature.geometry.type === "Polygon") {
                        multiPolygonCoords.push(feature.geometry.coordinates);
                    }

                    if (feature.geometry.type === "MultiPolygon") {
                        feature.geometry.coordinates.forEach(coords => {
                            multiPolygonCoords.push(coords);
                        });
                    }

                });

                jurisdiccionesFeatures.push({
                    type: "Feature",
                    geometry: {
                        type: "MultiPolygon",
                        coordinates: multiPolygonCoords
                    },
                    properties: {
                        jurisdiccion: nombreJur
                    }
                });
            }

            
            jurisdiccionesGeoJSON = {
                type: "FeatureCollection",
                features: jurisdiccionesFeatures
            };

            // ===============================
            // 4️⃣ Agregar capa al mapa
            // ===============================

            map.addSource('jurisdicciones', {
                type: 'geojson',
                data: jurisdiccionesGeoJSON
            });

            map.addLayer({
                id: 'jurisdicciones-fill',
                type: 'fill',
                source: 'jurisdicciones',
                layout: { visibility: 'none' },
                paint: {
                    'fill-color': '#16a34a',
                    'fill-opacity': 0.15
                }
            });

            map.addLayer({
                id: 'jurisdicciones-line',
                type: 'line',
                source: 'jurisdicciones',
                layout: { visibility: 'none' },
                paint: {
                    'line-color': '#14532d',
                    'line-width': 2
                }
            });            


            
        } catch (error) {
            console.error("Error cargando unidades:", error);
        }

    });



    //Evento del filtro para jurisdicciones
    document.getElementById('filtroJurisdiccion')
    .addEventListener('change', function () {

        const valor = this.value;

        // Si es "Todas"
        if (!valor) {

            map.setFilter('jurisdicciones-fill', null);
            map.setFilter('jurisdicciones-line', null);

            return;
        }

        // Mostrar solo la seleccionada
        map.setFilter('jurisdicciones-fill', [
            '==',
            ['get', 'jurisdiccion'],
            valor
        ]);

        map.setFilter('jurisdicciones-line', [
            '==',
            ['get', 'jurisdiccion'],
            valor
        ]);

    });


    async function cargarMunicipios() {

        const response = await fetch('/gis/api/municipios');
        const municipios = await response.json();

        const select = document.getElementById('filtroMunicipio');

        municipios.forEach(m => {
            const option = document.createElement('option');
            option.value = m.municipio;
            option.textContent = m.municipio;
            select.appendChild(option);
        });
    }

    cargarMunicipios();



    function aplicarFiltros() {

        const institucion = document.getElementById('filtroInstitucion').value;
        const nivel = document.getElementById('filtroNivel').value;
        const jurisdiccion = document.getElementById('filtroJurisdiccion').value;
        const municipioSelect = document.getElementById('filtroMunicipio');

        let municipiosSeleccionados = Array.from(municipioSelect.selectedOptions)
            .map(option => option.value);

        if (municipiosSeleccionados.includes("")) {
            municipiosSeleccionados = [];
        }


        // ===============================
        // 🔥 CONSTRUIR FILTROS DE UNIDADES
        // ===============================


        let filtros = ['all'];

        const institucionActiva = institucion && institucion.trim() !== "";
        const nivelActivo = nivel && nivel.trim() !== "";
        const jurisdiccionActiva = jurisdiccion && jurisdiccion.trim() !== "";
        const municipiosActivos = municipiosSeleccionados.length > 0;

        // Institución
        if (institucionActiva) {
            filtros.push(['==', ['get', 'institucion'], institucion]);
        }

        // Nivel
        if (nivelActivo) {
            filtros.push(['==', ['get', 'nivel_atencion'], nivel]);
        }

        // Jurisdicción
        if (jurisdiccionActiva) {
            filtros.push(['==', ['get', 'jurisdiccion'], jurisdiccion]);
        }

        // Municipio
        if (municipiosActivos) {
            filtros.push([
                'in',
                ['get', 'municipio'],
                ['literal', municipiosSeleccionados]
            ]);
        }

        // Aplicar filtro limpio
        map.setFilter('unidades-layer', filtros.length > 1 ? filtros : null);

        // ===============================
        // 🔥 CONTROL TERRITORIAL
        // ===============================

        // Caso Municipios
        if (municipiosSeleccionados.length > 0) {

            map.setLayoutProperty('jurisdicciones-fill', 'visibility', 'none');
            map.setLayoutProperty('jurisdicciones-line', 'visibility', 'none');

            map.setFilter('municipios-fill', [
                'in',
                ['get', 'NOMGEO'],
                ['literal', municipiosSeleccionados]
            ]);

            map.setPaintProperty('municipios-fill', 'fill-opacity', 0.3);

            const municipiosFiltrados = municipiosData.features.filter(f =>
                municipiosSeleccionados.includes(f.properties.NOMGEO)
            );

            if (municipiosFiltrados.length > 0) {
                const bbox = turf.bbox({
                    type: "FeatureCollection",
                    features: municipiosFiltrados
                });

                map.fitBounds(bbox, {
                    padding: 40,
                    duration: 800
                });
            }

        }
        // Caso Jurisdicción
        else if (jurisdiccion) {

            map.setLayoutProperty('jurisdicciones-fill', 'visibility', 'visible');
            map.setLayoutProperty('jurisdicciones-line', 'visibility', 'visible');

            map.setFilter('jurisdicciones-fill', [
                '==',
                ['to-upper', ['get', 'jurisdiccion']],
                jurisdiccion.trim().toUpperCase()
            ]);

            map.setFilter('jurisdicciones-line', [
                '==',
                ['to-upper', ['get', 'jurisdiccion']],
                jurisdiccion.trim().toUpperCase()
            ]);

            map.setFilter('municipios-fill', null);
            map.setPaintProperty('municipios-fill', 'fill-opacity', 0);

            const feature = jurisdiccionesGeoJSON.features.find(f =>
                f.properties.jurisdiccion.trim().toUpperCase() ===
                jurisdiccion.trim().toUpperCase()
            );

            if (feature) {
                const bbox = turf.bbox(feature);

                map.fitBounds(bbox, {
                    padding: 40,
                    duration: 800
                });
            }

        }
        // Nada territorial
        else {

            map.setLayoutProperty('jurisdicciones-fill', 'visibility', 'none');
            map.setLayoutProperty('jurisdicciones-line', 'visibility', 'none');

            map.setFilter('municipios-fill', null);
            map.setPaintProperty('municipios-fill', 'fill-opacity', 0);

            if (!institucion && !nivel) {
                map.fitBounds(estadoBBox, {
                    padding: 40,
                    duration: 800
                });
            }

        }

    }




    function limpiarFiltros() {

        document.getElementById('filtroInstitucion').value = "";
        document.getElementById('filtroNivel').value = "";
        document.getElementById('filtroJurisdiccion').value = "";
        
        // Limpiar select múltiple correctamente
        const municipioSelect = document.getElementById('filtroMunicipio');
        Array.from(municipioSelect.options).forEach(option => option.selected = false);

        map.setFilter('unidades-layer', null);
        
        //Quitar resaltado al limpiar
        map.setFilter('municipios-fill', null);
        map.setPaintProperty('municipios-fill', 'fill-opacity', 0);        


        // Ocultar jurisdicciones
        map.setLayoutProperty('jurisdicciones-fill', 'visibility', 'none');
        map.setLayoutProperty('jurisdicciones-line', 'visibility', 'none');
        map.setFilter('jurisdicciones-fill', null);
        map.setFilter('jurisdicciones-line', null);

        // Regresar a vista estatal
        if (estadoBBox) {
            map.fitBounds(estadoBBox, {
                padding: 40,
                duration: 800
            });
        }
    }

    // =========================
    // 3️⃣ EVENTOS DE SELECT
    // =========================

    document.getElementById('btnLimpiar')
        .addEventListener('click', limpiarFiltros);

    document.getElementById('filtroInstitucion')
        .addEventListener('change', aplicarFiltros);

    document.getElementById('filtroNivel')
        .addEventListener('change', aplicarFiltros);

    document.getElementById('filtroJurisdiccion')
    .addEventListener('change', aplicarFiltros);
        
    document.getElementById('filtroMunicipio')
        .addEventListener('change', aplicarFiltros);    

});
