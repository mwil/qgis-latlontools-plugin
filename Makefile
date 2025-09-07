PLUGINNAME = latlontools

# Detect OS and set appropriate plugin directory
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    PLUGINS = "$(HOME)"/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/$(PLUGINNAME)
    PYTHON = python3
else
    PLUGINS = "$(HOME)"/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/$(PLUGINNAME)
    PYTHON = python
endif

PY_FILES = __init__.py captureCoordinate.py captureExtent.py coordinateConverter.py copyLatLonTool.py dialog_manager.py digitizer.py ecef.py enhanced_settings.py extent_operations.py field2geom.py geohash.py geom2field.py geom2wkt.py georef.py input_validation.py latLonFunctions.py latLonTools.py latLonToolsProcessing.py lazy_loader.py maidenhead.py mapProviders.py mgrs.py mgrstogeom.py multizoom.py olc.py parser_service.py pluscodes.py plugin_cleanup.py plugin_enhancements.py provider.py run_all_tests.py settings.py showOnMapTool.py smart_parser.py text_preservation.py tomgrs.py ups.py util.py utm.py wkt2layers.py zoomToLatLon.py
EXTRAS = metadata.txt icon.png LICENSE

deploy:
	mkdir -p $(PLUGINS)
	mkdir -p $(PLUGINS)/i18n
	cp -vf i18n/latlonTools_fr.qm $(PLUGINS)/i18n
	cp -vf i18n/latlonTools_zh.qm $(PLUGINS)/i18n
	cp -vf $(PY_FILES) $(PLUGINS)
	cp -vf $(EXTRAS) $(PLUGINS)
	cp -vfr images $(PLUGINS)
	cp -vfr ui $(PLUGINS)
	cp -vfr doc $(PLUGINS)
	cp -vfr tests $(PLUGINS)
	cp -vf helphead.html index.html
	if [ -d .venv ]; then \
		source .venv/bin/activate && $(PYTHON) -m markdown -x extra readme.md >> index.html; \
	else \
		$(PYTHON) -m markdown -x extra readme.md >> index.html; \
	fi
	echo '</body>' >> index.html
	cp -vf index.html $(PLUGINS)/index.html

# Test commands
test: 
	$(PYTHON) run_tests.py

test-unit:
	$(PYTHON) run_tests.py --type unit

test-validation:
	$(PYTHON) run_tests.py --type validation

test-verbose:
	$(PYTHON) run_tests.py --verbose

# Run specific comprehensive test suites
test-flipping:
	$(PYTHON) tests/validation/test_coordinate_flipping_comprehensive.py

test-realworld:
	$(PYTHON) tests/validation/test_real_world_coordinate_scenarios.py

test-comprehensive: test-flipping test-realworld
	@echo "🎉 Comprehensive coordinate flipping tests completed"

# Clean up test artifacts
test-clean:
	find tests/ -name "*.pyc" -delete
	find tests/ -name "__pycache__" -type d -exec rm -rf {} +

.PHONY: test test-unit test-validation test-verbose test-flipping test-realworld test-comprehensive test-clean
