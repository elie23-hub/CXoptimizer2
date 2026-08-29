' Build a macro-enabled template with chart VBA (run once if needed).
Option Explicit
Dim xl, wb, vbProj, vbComp, code, outPath
On Error Resume Next
outPath = WScript.Arguments(0)
If outPath = "" Then
  WScript.Echo "Usage: cscript make_gap_xlsm_template.vbs <out.xlsm>"
  WScript.Quit 1
End If

Set xl = CreateObject("Excel.Application")
If Err.Number <> 0 Then
  WScript.Echo "Excel not available: " & Err.Description
  WScript.Quit 2
End If
xl.Visible = False
xl.DisplayAlerts = False
Set wb = xl.Workbooks.Add

code = "Option Explicit" & vbCrLf & _
"Public Sub BuildAllQuadrantCharts()" & vbCrLf & _
"  Dim ws As Worksheet" & vbCrLf & _
"  For Each ws In ThisWorkbook.Worksheets" & vbCrLf & _
"    If Left$(ws.Name, 1) <> ""_"" Then BuildQuadrantChartOnSheet ws" & vbCrLf & _
"  Next ws" & vbCrLf & _
"End Sub" & vbCrLf & _
"Public Sub BuildQuadrantChartOnSheet(ByVal ws As Worksheet)" & vbCrLf & _
"  Dim hdr As Long, firstData As Long, lastRow As Long, zxCol As Long, zyCol As Long" & vbCrLf & _
"  Dim r As Long, c As Long, i As Long, shp As Shape, cht As Chart, anchorRow As Long" & vbCrLf & _
"  On Error Resume Next" & vbCrLf & _
"  For i = ws.ChartObjects.Count To 1 Step -1: ws.ChartObjects(i).Delete: Next i" & vbCrLf & _
"  On Error GoTo 0" & vbCrLf & _
"  zxCol = 0: zyCol = 0: hdr = 0" & vbCrLf & _
"  For r = 1 To 30" & vbCrLf & _
"    For c = 1 To 20" & vbCrLf & _
"      If UCase$(Trim$(CStr(ws.Cells(r, c).Value))) = ""Z_X"" Then" & vbCrLf & _
"        zxCol = c: zyCol = c + 1: hdr = r: Exit For" & vbCrLf & _
"      End If" & vbCrLf & _
"    Next c" & vbCrLf & _
"    If zxCol > 0 Then Exit For" & vbCrLf & _
"  Next r" & vbCrLf & _
"  If zxCol = 0 Then Exit Sub" & vbCrLf & _
"  firstData = hdr + 1" & vbCrLf & _
"  lastRow = firstData" & vbCrLf & _
"  Do While IsNumeric(ws.Cells(lastRow, zxCol).Value) And ws.Cells(lastRow, zxCol).Value <> """"" & vbCrLf & _
"    lastRow = lastRow + 1" & vbCrLf & _
"    If lastRow > 20000 Then Exit Do" & vbCrLf & _
"  Loop" & vbCrLf & _
"  lastRow = lastRow - 1" & vbCrLf & _
"  If lastRow < firstData Then Exit Sub" & vbCrLf & _
"  Set shp = ws.Shapes.AddChart2(240, 75)" & vbCrLf & _
"  Set cht = shp.Chart" & vbCrLf & _
"  On Error Resume Next" & vbCrLf & _
"  Do While cht.SeriesCollection.Count > 0: cht.SeriesCollection(1).Delete: Loop" & vbCrLf & _
"  On Error GoTo 0" & vbCrLf & _
"  cht.SeriesCollection.NewSeries" & vbCrLf & _
"  With cht.SeriesCollection(1)" & vbCrLf & _
"    .Name = ""Statements""" & vbCrLf & _
"    .XValues = ws.Range(ws.Cells(firstData, zxCol), ws.Cells(lastRow, zxCol))" & vbCrLf & _
"    .Values = ws.Range(ws.Cells(firstData, zyCol), ws.Cells(lastRow, zyCol))" & vbCrLf & _
"    .MarkerStyle = 8: .MarkerSize = 7" & vbCrLf & _
"  End With" & vbCrLf & _
"  cht.HasTitle = True" & vbCrLf & _
"  cht.ChartTitle.Text = ""Importance vs performance (quadrant analysis)""" & vbCrLf & _
"  cht.Axes(1).HasTitle = True: cht.Axes(1).AxisTitle.Text = ""Z performance (X)""" & vbCrLf & _
"  cht.Axes(2).HasTitle = True: cht.Axes(2).AxisTitle.Text = ""Z importance (Y)""" & vbCrLf & _
"  cht.HasLegend = False" & vbCrLf & _
"  anchorRow = 0" & vbCrLf & _
"  If IsNumeric(ws.Range(""J1"").Value) Then anchorRow = CLng(ws.Range(""J1"").Value)" & vbCrLf & _
"  If anchorRow <= 0 Then anchorRow = lastRow + 3" & vbCrLf & _
"  shp.Left = ws.Cells(anchorRow, 1).Left" & vbCrLf & _
"  shp.Top = ws.Cells(anchorRow, 1).Top" & vbCrLf & _
"  shp.Width = 520: shp.Height = 340" & vbCrLf & _
"End Sub"

Err.Clear
Set vbProj = wb.VBProject
If Err.Number <> 0 Then
  WScript.Echo "Cannot access VBProject (enable Trust access to VBA project object model). " & Err.Description
  wb.Close False
  xl.Quit
  WScript.Quit 3
End If

Set vbComp = vbProj.VBComponents.Add(1)
vbComp.Name = "GapCharts"
vbComp.CodeModule.AddFromString code

' Also put Workbook_Open in ThisWorkbook
Dim tw
Set tw = vbProj.VBComponents("ThisWorkbook")
tw.CodeModule.AddFromString "Private Sub Workbook_Open()" & vbCrLf & "  BuildAllQuadrantCharts" & vbCrLf & "End Sub"

wb.SaveAs outPath, 52
wb.Close False
xl.Quit
WScript.Echo "OK " & outPath
