class EntriesController < ApplicationController
  def index
    @entries = Entry.all
    html = "<h1>Wiki Entries</h1><ul>"
    @entries.each do |entry|
      html += "<li><a href='/entries/#{entry.id}'>#{entry.title}</a></li>"
    end
    html += "</ul>"
    render html: html.html_safe
  end

  def show
    @entry = Entry.find(params[:id])
    
    # Get contributors from edits
    contributors = @entry.edits.pluck(:modified_by).uniq.join(", ")
    
    html = "<h1>#{@entry.title}</h1>"
    html += "<p>#{@entry.content}</p>"
    html += "<hr>"
    html += "<p><strong>Last Modified:</strong> #{@entry.updated_at}</p>"
    html += "<p><strong>Contributors:</strong> #{contributors}</p>"
    html += "<p><a href='/entries/#{@entry.id}/edits'>View History</a></p>"
    html += "<a href='/entries'>Back to List</a>"
    
    render html: html.html_safe
  end

  def create
    entry = Entry.create!(
      title: params[:title],
      content: params[:content],
      last_modified_by: params[:createdBy]
    )
    
    # Create initial edit record
    entry.edits.create!(
      content: params[:content],
      modified_by: params[:createdBy],
      summary: "Initial creation"
    )
    
    render json: entry, status: :created
  end

  def update
    @entry = Entry.find(params[:id])
    
    # Save history
    @entry.edits.create!(
      content: params[:content],
      modified_by: params[:modifiedBy],
      summary: params[:summary]
    )
    
    @entry.update!(
      content: params[:content],
      last_modified_by: params[:modifiedBy]
    )
    
    render json: @entry
  end
end