Copy Init.py, InitGui.py, protocol.py, and service.py into:

  <FreeCAD user directory>/Mod/FreeCADMCPBridge/

Then restart FreeCAD and run:

  import InitGui
  InitGui.start_bridge()

The adapter process can then be started separately with:

  freecad-mcp-adapter
