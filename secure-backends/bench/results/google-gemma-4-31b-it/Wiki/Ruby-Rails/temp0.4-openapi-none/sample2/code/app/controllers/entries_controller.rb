class EntriesController < ApplicationController
  def index
    @entries = Entry.all
    # The schema asks for text/html response for the list
    html_content = "<h1>Wiki Entries</h1><ul>"
    @entries.each do |entry|
      html_content += "<li><a href='/entries/#{entry.id}'>#{entry.title}</a></li>"
    end
    html_content += "</ul>"
    render html: html_content.html_safe
  end

  def create
    entry = Entry.new(entry_params)
    # The schema NewEntry includes createdBy, which we use for the first edit record
    creator = params[:createdBy] || "Anonymous"
    
    if entry.save
      # Create initial history record
      entry.edits.create!(
        content: entry.content,
        modified_by: creator,
        summary: "Initial creation"
      )
      render json: entry, status: :created
    else
      render json: entry.errors, status: :unprocessable_entity
    end
  end

  def show
    @entry = Entry.find(params[:id])
    # The schema asks for text/html response for the entry
    html_content = "<h1>#{@entry.title}</h1>"
    html_content += "<p>#{@entry.content}</p>"
    html_content += "<hr><p>Last modified by: #{@entry.last_modified_by} at #{@entry.updated_at}</p>"
    html_content += "<p><a href='/entries/#{@entry.id}/edits'>View History</a></p>"
    render html: html_content.html_safe
  end

  def update
    @entry = Entry.find(params[:id])
    update_params = params.require(:update_entry) # Matching UpdateEntry schema logic
    
    # We wrap this in a transaction to ensure both entry and edit history are updated
    Entry.transaction do
      @entry.update!(
        content: update_params[:content],
        last_modified_by: update_params[:modifiedBy]
      )
      
      @entry.edits.create!(
        content: update_params[:content],
        modified_by: update_params[:modifiedBy],
        summary: update_params[:summary]
      )
    end

    render json: @entry
  rescue ActiveRecord::RecordNotFound
    render json: { error: "Not Found" }, status: :not_found
  end

  def edits
    @entry = Entry.find(params[:id])
    @edits = @entry.edits.order(created_at: :desc)
    
    html_content = "<h1>Edit History for #{@entry.title}</h1>"
    html_content += "<table><tr><th>Date</th><th>User</th><th>Summary</th><th>Content</th></tr>"
    
    @edits.each do |edit|
      html_content += "<tr><td>#{edit.created_at}</td><td>#{edit.modified_by}</td><td>#{edit.summary}</td><td>#{edit.content}</td></tr>"
    end
    
    html_content += "</table><p><a href='/entries/#{@entry.id}'>Back to Entry</a></p>"
    render html: html_content.html_safe
  end

  private

  def entry_params
    params.permit(:title, :content)
  end
end