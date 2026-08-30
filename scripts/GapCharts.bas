Option Explicit

' Rebuild section quadrant charts to match the app biplot:
' - Equal axis dimensions (same +/- extent on X and Y from z-scores)
' - Origin (0,0) dead-center — not shifted by asymmetric data ranges
' - Square, centered chart under columns A:H
' - Markers only (no connecting lines), labels from Label column
' - Marker + soft quadrant fills by Quadrant column
' - Title from I1 (section name) or sheet name

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
  Dim extent As Double, v As Double, majorStep As Double
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
  ' Skip subtitle / note rows until numeric Z_X values begin
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

  ' Square chart, centered under columns A:H (not left-shifted)
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
      .Font.Color = RGB(0, 0, 0)
    End With

    ' Prefer Value-From-Cells (Label column); fall back to per-point text
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

    ' Excel only draws scatter leader lines when labels are moved off the marker.
    ' Offset each label so a connector line appears from point -> label.
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
    .Font.Color = RGB(0, 0, 0)
  End With
  cht.HasLegend = False

  ' Same half-extent on X and Y: Max(|z| + 0.45, 2.5) — origin stays centered
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
  majorStep = Application.WorksheetFunction.Round(extent / 5#, 2)
  If majorStep <= 0 Then majorStep = 0.5

  With cht.Axes(xlCategory)
    .HasTitle = True
    .AxisTitle.Text = "Performance (z)"
    .AxisTitle.Font.Size = 10
    .AxisTitle.Font.Color = RGB(107, 114, 128)
    .MinimumScale = -extent
    .MaximumScale = extent
    .MajorUnit = majorStep
    .MinorUnit = majorStep / 2#
    .Crosses = xlAxisCrossesCustom
    .CrossesAt = 0
    .TickLabelPosition = xlTickLabelPositionNone
    .TickLabels.Font.Size = 9
    .TickLabels.Font.Color = RGB(156, 163, 175)
    .Border.Color = RGB(201, 206, 216)
    .Border.Weight = xlHairline
    On Error Resume Next
    .HasMajorGridlines = False
    .HasMinorGridlines = False
    .MajorGridlines.Delete
    .MinorGridlines.Delete
    On Error GoTo 0
  End With

  With cht.Axes(xlValue)
    .HasTitle = True
    .AxisTitle.Text = "Importance (z)"
    .AxisTitle.Font.Size = 10
    .AxisTitle.Font.Color = RGB(107, 114, 128)
    .MinimumScale = -extent
    .MaximumScale = extent
    .MajorUnit = majorStep
    .MinorUnit = majorStep / 2#
    .Crosses = xlAxisCrossesCustom
    .CrossesAt = 0
    .TickLabelPosition = xlTickLabelPositionNone
    .TickLabels.Font.Size = 9
    .TickLabels.Font.Color = RGB(156, 163, 175)
    .Border.Color = RGB(201, 206, 216)
    .Border.Weight = xlHairline
    On Error Resume Next
    .HasMajorGridlines = False
    .HasMinorGridlines = False
    .MajorGridlines.Delete
    .MinorGridlines.Delete
    On Error GoTo 0
  End With

  ' Force a square plot area centered in the chart (equal visual quadrants)
  On Error Resume Next
  cht.ChartArea.Format.Fill.ForeColor.RGB = RGB(255, 255, 255)
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
  cht.ChartArea.Format.Line.Visible = msoFalse
  On Error GoTo 0

  Call AddQuadrantFills(cht)
End Sub

Private Sub AddQuadrantFills(ByVal cht As Chart)
  Dim pl As Double, pt As Double, pw As Double, ph As Double
  Dim sh As Shape
  Dim i As Long

  On Error Resume Next
  For i = cht.Shapes.Count To 1 Step -1
    If Left$(cht.Shapes(i).Name, 3) = "Q_" Then cht.Shapes(i).Delete
  Next i

  pl = cht.PlotArea.InsideLeft
  pt = cht.PlotArea.InsideTop
  pw = cht.PlotArea.InsideWidth
  ph = cht.PlotArea.InsideHeight
  If pw <= 0 Or ph <= 0 Then Exit Sub

  Set sh = cht.Shapes.AddShape(msoShapeRectangle, pl, pt, pw / 2, ph / 2)
  sh.Name = "Q_Urgent"
  sh.Fill.ForeColor.RGB = RGB(244, 204, 204)
  sh.Fill.Transparency = 0.35
  sh.Line.Visible = msoFalse
  sh.ZOrder msoSendToBack

  Set sh = cht.Shapes.AddShape(msoShapeRectangle, pl + pw / 2, pt, pw / 2, ph / 2)
  sh.Name = "Q_Maintain"
  sh.Fill.ForeColor.RGB = RGB(217, 234, 211)
  sh.Fill.Transparency = 0.35
  sh.Line.Visible = msoFalse
  sh.ZOrder msoSendToBack

  Set sh = cht.Shapes.AddShape(msoShapeRectangle, pl, pt + ph / 2, pw / 2, ph / 2)
  sh.Name = "Q_Low"
  sh.Fill.ForeColor.RGB = RGB(255, 242, 204)
  sh.Fill.Transparency = 0.25
  sh.Line.Visible = msoFalse
  sh.ZOrder msoSendToBack

  Set sh = cht.Shapes.AddShape(msoShapeRectangle, pl + pw / 2, pt + ph / 2, pw / 2, ph / 2)
  sh.Name = "Q_Overkill"
  sh.Fill.ForeColor.RGB = RGB(207, 226, 243)
  sh.Fill.Transparency = 0.35
  sh.Line.Visible = msoFalse
  sh.ZOrder msoSendToBack

  Call AddCornerLabel(cht, "Q_L_Urgent", "Low performance high importance", pl + 4, pt + 4, RGB(122, 16, 16))
  Call AddCornerLabel(cht, "Q_L_Maintain", "High performance high importance", pl + pw / 2 + 4, pt + 4, RGB(45, 90, 26))
  Call AddCornerLabel(cht, "Q_L_Low", "Low performance low importance", pl + 4, pt + ph / 2 + 4, RGB(138, 104, 0))
  Call AddCornerLabel(cht, "Q_L_Overkill", "High performance low importance", pl + pw / 2 + 4, pt + ph / 2 + 4, RGB(13, 63, 150))
  On Error GoTo 0
End Sub

Private Sub AddCornerLabel(ByVal cht As Chart, ByVal nm As String, ByVal txt As String, _
                           ByVal leftPos As Double, ByVal topPos As Double, ByVal fontRgb As Long)
  Dim tb As Shape
  On Error Resume Next
  Set tb = cht.Shapes.AddTextbox(msoTextOrientationHorizontal, leftPos, topPos, 170, 28)
  tb.Name = nm
  tb.Fill.Visible = msoFalse
  tb.Line.Visible = msoFalse
  tb.TextFrame.Characters.Text = txt
  tb.TextFrame.Characters.Font.Size = 8
  tb.TextFrame.Characters.Font.Bold = True
  tb.TextFrame.Characters.Font.Color = fontRgb
  On Error GoTo 0
End Sub
