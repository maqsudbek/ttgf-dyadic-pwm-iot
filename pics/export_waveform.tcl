# GTKWave Tcl script to export waveform as PNG
set fst_file "../test/tb.fst"
set gtkw_file "../test/tb.gtkw"
set out_png "waveform.png"

gtkwave::loadFile $fst_file
gtkwave::readSaveFile $gtkw_file

# Export to PNG using the print command
gtkwave::/File/Print_To_File "PNG" $out_png {Full Size {1000 600}} {Landscape}
puts "Waveform exported to $out_png"
