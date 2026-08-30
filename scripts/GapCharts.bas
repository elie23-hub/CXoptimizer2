Option Explicit

' Quadrant biplot charts (matches reference export):
' - Equal +/- z scale on X and Y, origin at plot centre
' - Centre crosshair axes (X/Y cross at z=0), not edge box lines
' - Axis titles, no tick numbers, no gridlines, no plot border
' - Markers coloured by Quadrant, labels from Label column + leader lines

Private Const CLR_AXIS As Long = 9843336      ' RGB(201, 206, 216)
Private Const CLR_TITLE As Long = 7039855     ' RGB(107, 114, 128)
Private Const CLR_LABEL As Long = 0           ' RGB(0, 0, 0)

Public Sub BuildAllQuadrantCharts()
  Dim ws As Worksheet
  For Each ws In ThisWorkbook.Worksheets
    If Left$(ws.Name, 1) <> "_" Then BuildOne ws
  Next ws
End Sub

Public Sub BuildOne(ByVal ws As Worksheet)
  Dim hdr As Long, firstData As Long, lastRow As Long
  Dim zxCol As Long, zyCol As Long, labelCol As Long, qCol As Long
  Dim r As Long, c As Long, i As Long, pt As Long
  Dim co As ChartObject, cht As Chart, ser As Series
  Dim anchorRow As Long, chartTitle As String, lbl As String, q As String
  Dim labelAddr As String
  Dim extent As Double, v As Double
  Dim chartW As Double, chartH As Double, tableW As Double, leftPos As Double
  Dim plotSide As Double, plotLeft As Double, plotTop As Double
  Dim rgbCol As Long

  On Error Resume Next
  For i = ws.ChartObjects.Count To 1 Step -1
    ws.ChartObjects(i).Delete
  Next i
  On Error GoTo 0

  zxCol = 0: zyCol = 0: labelCol = 0: qCol = 0: hdr = 0
  For r = 1 To 60
    For c = 8 To 20
      If UCase$(Trim$(CStr(ws.Cells(r, c).Value))) = "Z_X" Then
        zxCol = c
        zyCol = c + 1
        qCol = c + 2
        labelCol = c + 3
        hdr = r
        Exit For
      End If
    Next c
    If zxCol > 0 Then Exit For
  Next r
  If zxCol = 0 Then Exit Sub

  firstData = hdr + 1
  Do While firstData < hdr + 6
    If IsNumeric(ws.Cells(firstData, zxCol).Value) And _
       CStr(ws.Cells(firstData, zxCol).Value) <> "" Then Exit Do
    firstData = firstData + 1
  Loop

  lastRow = firstData
  Do While IsNumeric(ws.Cells(lastRow, zxCol).Value) And CStr(ws.Cells(lastRow, zxCol).Value) <> ""
    lastRow = lastRow + 1
    If lastRow > 20000 Then Exit Do
  Loop
  lastRow = lastRow - 1
  If lastRow < firstData Then Exit Sub

  chartTitle = Trim$(CStr(ws.Range("I1").Value))
  If chartTitle = "" Then chartTitle = ws.Name

  anchorRow = 0
  If IsNumeric(ws.Range("J1").Value) Then anchorRow = CLng(ws.Range("J1").Value)
  If anchorRow <= 0 Then anchorRow = lastRow + 3

  chartW = 480
  chartH = 480
  tableW = ws.Range("A1:H1").Width
  leftPos = ws.Range("A1").Left + (tableW - chartW) / 2#
  If leftPos < ws.Range("A1").Left Then leftPos = ws.Range("A1").Left

  Set co = ws.ChartObjects.Add( _
      Left:=leftPos, _
      Top:=ws.Cells(anchorRow, 1).Top, _
      Width:=chartW, Height:=chartH)
  Set cht = co.Chart
  cht.ChartType = xlXYScatter

  On Error Resume Next
  Do While cht.SeriesCollection.Count > 0
    cht.SeriesCollection(1).Delete
  Loop
  On Error GoTo 0

  cht.SeriesCollection.NewSeries
  Set ser = cht.SeriesCollection(1)
  With ser
    .Name = chartTitle
    .XValues = ws.Range(ws.Cells(firstData, zxCol), ws.Cells(lastRow, zxCol))
    .Values = ws.Range(ws.Cells(firstData, zyCol), ws.Cells(lastRow, zyCol))
    .MarkerStyle = xlMarkerStyleCircle
    .MarkerSize = 7

    On Error Resume Next
    .Format.Line.Visible = msoFalse
    .Border.LineStyle = xlLineStyleNone
    .Smooth = False
    On Error GoTo 0

    For pt = 1 To .Points.Count
      q = LCase$(Trim$(CStr(ws.Cells(firstData + pt - 1, qCol).Value)))
      Select Case q
        Case "urgent"
          rgbCol = RGB(153, 0, 0)
        Case "maintain"
          rgbCol = RGB(56, 118, 29)
        Case "low"
          rgbCol = RGB(191, 144, 0)
        Case "overkill"
          rgbCol = RGB(17, 85, 204)
        Case Else
          rgbCol = RGB(46, 117, 182)
      End Select
      On Error Resume Next
      .Points(pt).MarkerBackgroundColor = rgbCol
      .Points(pt).MarkerForegroundColor = rgbCol
      .Points(pt).Format.Line.Visible = msoFalse
      On Error GoTo 0
    Next pt

    .HasDataLabels = True
    With .DataLabels
      .ShowValue = False
      .ShowCategoryName = False
      .ShowSeriesName = False
      .ShowLegendKey = False
      .ShowBubbleSize = False
      .ShowPercentage = False
      .ShowLeaderLines = True
      .Position = xlLabelPositionRight
      .Font.Name = "Calibri"
      .Font.Size = 8
      .Font.Color = CLR_LABEL
    End With

    labelAddr = "='" & Replace(ws.Name, "'", "''") & "'!" & _
                ws.Range(ws.Cells(firstData, labelCol), ws.Cells(lastRow, labelCol)).Address(True, True)
    On Error Resume Next
    .DataLabels.ShowRange = True
    .DataLabels.Format.TextFrame2.TextRange.InsertChartField _
        msoChartFieldRange, labelAddr, 0
    If Err.Number <> 0 Then
      Err.Clear
      For pt = 1 To .Points.Count
        lbl = CStr(ws.Cells(firstData + pt - 1, labelCol).Value)
        .Points(pt).DataLabel.Text = lbl
      Next pt
    End If
    On Error GoTo 0

    For pt = 1 To .Points.Count
      On Error Resume Next
      With .Points(pt).DataLabel
        .ShowLeaderLines = True
        .ShowLegendKey = False
        .ShowSeriesName = False
        .Position = xlLabelPositionRight
        Select Case ((pt - 1) Mod 4)
          Case 0
            .Left = .Left + 36
            .Top = .Top - 22
          Case 1
            .Left = .Left + 36
            .Top = .Top + 16
          Case 2
            .Left = .Left - 140
            .Top = .Top - 22
          Case 3
            .Left = .Left - 140
            .Top = .Top + 16
        End Select
      End With
      On Error GoTo 0
    Next pt
    On Error Resume Next
    .DataLabels.ShowLeaderLines = True
    On Error GoTo 0
  End With

  cht.HasTitle = True
  With cht.ChartTitle
    .Text = chartTitle
    .Font.Name = "Calibri"
    .Font.Size = 14
    .Font.Bold = True
    .Font.Color = CLR_LABEL
  End With
  cht.HasLegend = False

  extent = CalcExtent(ws, firstData, lastRow, zxCol, zyCol)
  Call ApplyBiplotAxes(cht, extent)
  Call SquarePlotArea(cht)
End Sub

Private Function CalcExtent( _
    ByVal ws As Worksheet, _
    ByVal firstData As Long, _
    ByVal lastRow As Long, _
    ByVal zxCol As Long, _
    ByVal zyCol As Long) As Double
  Dim r As Long
  Dim v As Double
  Dim extent As Double

  extent = 2.5
  For r = firstData To lastRow
    If IsNumeric(ws.Cells(r, zxCol).Value) Then
      v = Abs(CDbl(ws.Cells(r, zxCol).Value)) + 0.45
      If v > extent Then extent = v
    End If
    If IsNumeric(ws.Cells(r, zyCol).Value) Then
      v = Abs(CDbl(ws.Cells(r, zyCol).Value)) + 0.45
      If v > extent Then extent = v
    End If
  Next r
  CalcExtent = extent
End Function

Private Sub ApplyBiplotAxes(ByVal cht As Chart, ByVal extent As Double)
  ' Axes cross at z=0 => horizontal + vertical centre crosshair (not edge box lines).
  With cht.Axes(xlCategory)
    .HasTitle = True
    .AxisTitle.Text = "Performance (z)"
    .AxisTitle.Font.Name = "Calibri"
    .AxisTitle.Font.Size = 10
    .AxisTitle.Font.Color = CLR_TITLE
    .MinimumScale = -extent
    .MaximumScale = extent
    .Crosses = xlAxisCrossesCustom
    .CrossesAt = 0
    .TickLabelPosition = xlTickLabelPositionNone
    .MajorTickMark = xlTickMarkNone
    .MinorTickMark = xlTickMarkNone
    On Error Resume Next
    .Format.Line.Visible = msoTrue
    .Format.Line.ForeColor.RGB = CLR_AXIS
    .Format.Line.Weight = 0.75
    .Border.LineStyle = xlContinuous
    .Border.Color = CLR_AXIS
    .HasMajorGridlines = False
    .HasMinorGridlines = False
    .MajorGridlines.Delete
    .MinorGridlines.Delete
    On Error GoTo 0
  End With

  With cht.Axes(xlValue)
    .HasTitle = True
    .AxisTitle.Text = "Importance (z)"
    .AxisTitle.Font.Name = "Calibri"
    .AxisTitle.Font.Size = 10
    .AxisTitle.Font.Color = CLR_TITLE
    .MinimumScale = -extent
    .MaximumScale = extent
    .Crosses = xlAxisCrossesCustom
    .CrossesAt = 0
    .TickLabelPosition = xlTickLabelPositionNone
    .MajorTickMark = xlTickMarkNone
    .MinorTickMark = xlTickMarkNone
    On Error Resume Next
    .Format.Line.Visible = msoTrue
    .Format.Line.ForeColor.RGB = CLR_AXIS
    .Format.Line.Weight = 0.75
    .Border.LineStyle = xlContinuous
    .Border.Color = CLR_AXIS
    .HasMajorGridlines = False
    .HasMinorGridlines = False
    .MajorGridlines.Delete
    .MinorGridlines.Delete
    On Error GoTo 0
  End With
End Sub

Private Sub SquarePlotArea(ByVal cht As Chart)
  Dim plotSide As Double
  Dim plotLeft As Double
  Dim plotTop As Double

  On Error Resume Next
  cht.ChartArea.Format.Fill.ForeColor.RGB = RGB(255, 255, 255)
  cht.ChartArea.Format.Line.Visible = msoFalse
  plotSide = Application.WorksheetFunction.Min(cht.PlotArea.Width, cht.PlotArea.Height) * 0.92
  plotLeft = (cht.ChartArea.Width - plotSide) / 2#
  plotTop = cht.PlotArea.Top
  If plotTop < cht.ChartTitle.Top + cht.ChartTitle.Height + 8 Then _
      plotTop = cht.ChartTitle.Top + cht.ChartTitle.Height + 8
  cht.PlotArea.Width = plotSide
  cht.PlotArea.Height = plotSide
  cht.PlotArea.Left = plotLeft
  cht.PlotArea.Top = plotTop
  cht.PlotArea.Format.Fill.ForeColor.RGB = RGB(255, 255, 255)
  cht.PlotArea.Format.Line.Visible = msoFalse
  cht.PlotArea.Border.LineStyle = xlLineStyleNone
  On Error GoTo 0
End Sub
