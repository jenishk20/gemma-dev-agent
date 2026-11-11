class EditsController < ApplicationController
  # GET /entries/:entryId/edits
  def index
    @entry = Entry.find_by(id: params[:entryId])
    return render json: { error: "Not Found" }, status: :not_found unless @entry

    @edits = @entry.edits.order(created_at: :desc)
    
    html = "<h1>History for #{@entry.title}</h1><ul>"
    @edits.each_with_index do |edit, index|
      # Simple diff simulation: show content of this version
      html += "<li>"
      html += "<strong>#{edit.created_at}</strong> - #{edit.modified_by}<br>"
      html += "<em>Summary: #{edit.summary}</em><br>"
      html += "<pre>#{edit.content}</pre>"
      html += "</li><hr>"
    end
    html += "</ul>"
    html += "<a href='/entries/#{params[:entryId]}'>Back to Entry</a>"
    
    render html: html.html_safe
  end
end