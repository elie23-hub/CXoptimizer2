' Post-process gap export: create real Excel charts from Z_X / Z_Y ranges.
' Usage: cscript //nologo add_gap_charts.vbs <input.xlsx> <output.xlsx|xlsm>
Option Explicit
Dim xl, wb, ws, inPath, outPath, fso
Dim ext, fmt

inPath = WScript.Arguments(0)
outPath = WScript.Arguments(1)
If inPath = "" Or outPath = "" Then
  WScript.Echo "ERR usage"
  WScript.Quit 1
End If

Set fso = CreateObject("Scripting.FileSystemObject")
inPath = fso.GetAbsolutePathName(inPath)
outPath = fso.GetAbsolutePathName(outPath)
If Not fso.FileExists(inPath) Then
  WScript.Echo "ERR missing input"
  WScript.Quit 2
End If

On Error Resume Next
Set xl = CreateObject("Excel.Application")
If Err.Number <> 0 Then
  WScript.Echo "ERR no excel: " & Err.Description
  WScript.Quit 3
End If
Err.Clear

xl.Visible = False
xl.DisplayAlerts = False
xl.ScreenUpdating = False

Set wb = xl.Workbooks.Open(inPath)
If Err.Number <> 0 Then
  WScript.Echo "ERR open: " & Err.Description
  xl.Quit
  WScript.Quit 4
End If
Err.Clear

For Each ws In wb.Worksheets
  If Left(ws.Name, 1) <> "_" Then
    Call AddChartToSheet(ws)
  End If
Next

' Optional VBA inject (ignored if Trust Center blocks VBProject access)
Call InjectVba(wb)
Err.Clear

ext = LCase(fso.GetExtensionName(outPath))
If ext = "xlsm" Then
  fmt = 52
Else
  fmt = 51
End If

If fso.FileExists(outPath) Then fso.DeleteFile outPath, True
Err.Clear
wb.SaveAs outPath, fmt
If Err.Number <> 0 Then
  WScript.Echo "ERR save: " & Err.Description
  wb.Close False
  xl.Quit
  WScript.Quit 5
End If

wb.Close False
xl.Quit
WScript.Echo "OK"
WScript.Quit 0

Sub AddChartToSheet(ws)
  Dim hdr, firstData, lastRow, zxCol, zyCol, labelCol, r, c, i, pt
  Dim shp, cht, anchorRow, chartTitle, lbl

  On Error Resume Next
  For i = ws.ChartObjects.Count To 1 Step -1
    ws.ChartObjects(i).Delete
  Next
  Err.Clear

  zxCol = 0
  zyCol = 0
  labelCol = 0
  hdr = 0
  For r = 1 To 60
    For c = 8 To 20
      If UCase(Trim(CStr(ws.Cells(r, c).Value))) = "Z_X" Then
        zxCol = c
        zyCol = c + 1
        labelCol = c + 3
        hdr = r
        Exit For
      End If
    Next
    If zxCol > 0 Then Exit For
  Next
  If zxCol = 0 Then Exit Sub

  firstData = hdr + 1
  lastRow = firstData
  Do While IsNumeric(ws.Cells(lastRow, zxCol).Value) And CStr(ws.Cells(lastRow, zxCol).Value) <> ""
    lastRow = lastRow + 1
    If lastRow > 20000 Then Exit Do
  Loop
  lastRow = lastRow - 1
  If lastRow < firstData Then Exit Sub

  chartTitle = Trim(CStr(ws.Range("I1").Value))
  If chartTitle = "" Then chartTitle = ws.Name

  anchorRow = 0
  If IsNumeric(ws.Range("J1").Value) Then anchorRow = CLng(ws.Range("J1").Value)
  If anchorRow <= 0 Then anchorRow = lastRow + 3

  Err.Clear
  Set shp = ws.ChartObjects.Add(ws.Cells(anchorRow, 1).Left, ws.Cells(anchorRow, 1).Top, 540, 380)
  Set cht = shp.Chart
  cht.ChartType = 75 ' xlXYScatter
  Err.Clear

  Do While cht.SeriesCollection.Count > 0
    cht.SeriesCollection(1).Delete
  Loop
  Err.Clear

  cht.SeriesCollection.NewSeries
  With cht.SeriesCollection(1)
    .Name = chartTitle
    .XValues = ws.Range(ws.Cells(firstData, zxCol), ws.Cells(lastRow, zxCol))
    .Values = ws.Range(ws.Cells(firstData, zyCol), ws.Cells(lastRow, zyCol))
    .MarkerStyle = 8
    .MarkerSize = 7
    .MarkerBackgroundColor = RGB(46, 117, 182)
    .MarkerForegroundColor = RGB(46, 117, 182)
    .HasDataLabels = True
    .DataLabels.ShowValue = False
    .DataLabels.ShowCategoryName = False
    .DataLabels.ShowSeriesName = False
    For pt = 1 To .Points.Count
      lbl = CStr(ws.Cells(firstData + pt - 1, labelCol).Value)
      .Points(pt).DataLabel.Text = lbl
      .Points(pt).DataLabel.ShowLeaderLines = True
    Next
  End With

  cht.HasTitle = True
  cht.ChartTitle.Text = chartTitle
  cht.Axes(1).HasTitle = True
  cht.Axes(1).AxisTitle.Text = "Performance (z)"
  cht.Axes(2).HasTitle = True
  cht.Axes(2).AxisTitle.Text = "Importance (z)"
  cht.HasLegend = False
  Err.Clear
End Sub

Sub InjectVba(wb)
  Dim vbProj, vbComp, code, tw, n, exists
  On Error Resume Next
  Set vbProj = wb.VBProject
  If Err.Number <> 0 Then Exit Sub
  Err.Clear

  exists = False
  For n = 1 To vbProj.VBComponents.Count
    If vbProj.VBComponents(n).Name = "GapCharts" Then exists = True
  Next
  If exists Then Exit Sub

  code = "Option Explicit" & vbCrLf & _
    "Public Sub BuildAllQuadrantCharts()" & vbCrLf & _
    "  Dim ws As Worksheet" & vbCrLf & _
    "  For Each ws In ThisWorkbook.Worksheets" & vbCrLf & _
    "    If Left(ws.Name, 1) <> ""_"" Then BuildOne ws" & vbCrLf & _
    "  Next ws" & vbCrLf & _
    "End Sub" & vbCrLf & _
    "Public Sub BuildOne(ByVal ws As Worksheet)" & vbCrLf & _
    "  Dim hdr As Long, firstData As Long, lastRow As Long, zxCol As Long, zyCol As Long" & vbCrLf & _
    "  Dim r As Long, c As Long, i As Long, shp As Shape, cht As Chart, anchorRow As Long" & vbCrLf & _
    "  On Error Resume Next" & vbCrLf & _
    "  For i = ws.ChartObjects.Count To 1 Step -1: ws.ChartObjects(i).Delete: Next i" & vbCrLf & _
    "  On Error GoTo 0" & vbCrLf & _
    "  zxCol = 0: For r = 1 To 40: For c = 8 To 20" & vbCrLf & _
    "    If UCase(Trim(CStr(ws.Cells(r, c).Value))) = ""Z_X"" Then zxCol = c: zyCol = c + 1: hdr = r: Exit For" & vbCrLf & _
    "  Next c: If zxCol > 0 Then Exit For: Next r" & vbCrLf & _
    "  If zxCol = 0 Then Exit Sub" & vbCrLf & _
    "  firstData = hdr + 1: lastRow = firstData" & vbCrLf & _
    "  Do While IsNumeric(ws.Cells(lastRow, zxCol).Value) And CStr(ws.Cells(lastRow, zxCol).Value) <> """": lastRow = lastRow + 1: Loop" & vbCrLf & _
    "  lastRow = lastRow - 1: If lastRow < firstData Then Exit Sub" & vbCrLf & _
    "  Set shp = ws.Shapes.AddChart2(240, 75): Set cht = shp.Chart" & vbCrLf & _
    "  On Error Resume Next: Do While cht.SeriesCollection.Count > 0: cht.SeriesCollection(1).Delete: Loop: On Error GoTo 0" & vbCrLf & _
    "  cht.SeriesCollection.NewSeries" & vbCrLf & _
    "  With cht.SeriesCollection(1)" & vbCrLf & _
    "    .Name = ""Statements""" & vbCrLf & _
    "    .XValues = ws.Range(ws.Cells(firstData, zxCol), ws.Cells(lastRow, zxCol))" & vbCrLf & _
    "    .Values = ws.Range(ws.Cells(firstData, zyCol), ws.Cells(lastRow, zyCol))" & vbCrLf & _
    "    .MarkerStyle = 8: .MarkerSize = 7" & vbCrLf & _
    "  End With" & vbCrLf & _
    "  cht.HasTitle = True: cht.ChartTitle.Text = ""Importance vs performance (quadrant analysis)""" & vbCrLf & _
    "  cht.Axes(1).HasTitle = True: cht.Axes(1).AxisTitle.Text = ""Z performance (X)""" & vbCrLf & _
    "  cht.Axes(2).HasTitle = True: cht.Axes(2).AxisTitle.Text = ""Z importance (Y)""" & vbCrLf & _
    "  cht.HasLegend = False" & vbCrLf & _
    "  anchorRow = 0: If IsNumeric(ws.Range(""J1"").Value) Then anchorRow = CLng(ws.Range(""J1"").Value)" & vbCrLf & _
    "  If anchorRow <= 0 Then anchorRow = lastRow + 3" & vbCrLf & _
    "  shp.Left = ws.Cells(anchorRow, 1).Left: shp.Top = ws.Cells(anchorRow, 1).Top" & vbCrLf & _
    "  shp.Width = 520: shp.Height = 340" & vbCrLf & _
    "End Sub"

  Set vbComp = vbProj.VBComponents.Add(1)
  If Err.Number <> 0 Then Exit Sub
  vbComp.Name = "GapCharts"
  vbComp.CodeModule.AddFromString code

  Set tw = vbProj.VBComponents("ThisWorkbook")
  tw.CodeModule.AddFromString "Private Sub Workbook_Open()" & vbCrLf & "  BuildAllQuadrantCharts" & vbCrLf & "End Sub"
  Err.Clear
End Sub
