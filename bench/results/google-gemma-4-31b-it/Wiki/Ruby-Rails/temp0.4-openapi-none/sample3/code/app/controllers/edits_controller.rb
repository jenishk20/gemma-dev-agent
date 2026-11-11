class EditsController < ApplicationController
  def index
    @entry = Entry.find(params[:entryId])
    @edits = @entry.edits.order(created_at: :desc)
    
    html = "<h1>History for #{@entry.title}</h1><ul>"
    @edits.each_with_index do |edit, index|
      # Simple diff simulation: show content change from previous version
      prev_edit = @entry.edits.where("created_at < ?", edit.created_at).order(created_at: :desc).first
      diff = prev_edit ? "Changed from: #{prev_edit.content[0..50]}..." : "Initial version"
      
      html += "<li>"
      html += "<strong>#{edit.modified_by}</strong> (#{edit.created_at})<br>"
      html += "Summary: #{edit.summary}<br>"
      html += "<em>Diff: #{diff}</em>"
      html += "</li><br>"
    end
    html += "</ul>"
    html += "<a href='/entries/#{@entry.id}'>Back to Entry</a>"
    
    render html: html.html_safe
  end
end