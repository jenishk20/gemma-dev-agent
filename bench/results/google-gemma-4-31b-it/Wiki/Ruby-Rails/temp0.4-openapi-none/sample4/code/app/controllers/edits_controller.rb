class EditsController < ApplicationController
  # GET /entries/:entryId/edits
  def index
    @entry = Entry.find(params[:entryId])
    @edits = @entry.edits.order(created_at: :desc)

    html = "<h1>Edit History for #{@entry.title}</h1>"
    html += "<table><tr><th>Date</th><th>User</th><th>Summary</th><th>Content</th></tr>"
    
    @edits.each do |edit|
      html += "<tr><td>#{edit.created_at}</td><td>#{edit.modified_by}</td><td>#{edit.summary}</td><td>#{edit.content}</td></tr>"
    end
    
    html += "</table><br><a href='/entries/#{@entry.id}'>Back to Entry</a>"
    render html: html.html_safe
  end
end