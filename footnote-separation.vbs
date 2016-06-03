Sub UnLinkEndNotes()
	Dim eRng As Range, eNote As Endnote, i As Integer
	With ActiveDocument
	For Each eNote In .Endnotes
	With eNote
	i = .Index
	With .Reference.Characters.Last
	.InsertBefore i
	.Style = "Endnote Reference"
	End With
	.Range.Cut
	End With
	Set eRng = .Range
	With eRng
	.InsertAfter vbCr & i & ". "
	.Start = .End
	.Paste
	.Style = "Endnote Text"
	End With
	Next
	For Each eNote In .Endnotes
	eNote.Delete
	Next
	End With
End Sub
