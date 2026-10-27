.PHONY: install run gui web status connect disconnect check clean

install:
	@./install.sh

run: gui

gui:
	@python3 buds4pro_gtk.py

web:
	@python3 buds4pro_web.py

status:
	@python3 buds4ctl.py status

connect:
	@python3 buds4ctl.py connect

disconnect:
	@python3 buds4ctl.py disconnect

check:
	@python3 -m py_compile buds4pro_protocol.py buds4pro_gtk.py buds4pro_web.py buds4ctl.py

clean:
	@rm -rf __pycache__ *.pyc
