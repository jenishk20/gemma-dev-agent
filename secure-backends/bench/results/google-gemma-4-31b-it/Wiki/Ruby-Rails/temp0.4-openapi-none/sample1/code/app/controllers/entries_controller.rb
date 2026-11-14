class EntriesController < ApplicationController
  # GET /entries
  def index
    @entries = Entry.all
    html = "<h1>Wiki Entries</h1><ul>"
    @entries.each do |entry|
      html += "<li><a href='/entries/#{entry.id}'>#{entry.title}</a></li>"
    end
    html += "</ul>"
    render html: html.html_safe
  end

  # POST /entries
  def create
    entry = Entry.new(entry_params)
    if entry.save
      # Create the first edit record for tracking
      entry.edits.create!(
        content: entry.content,
        modified_by: params[:createdBy],
        summary: "Initial creation"
      )
      render json: entry, status: :created
    else
      render json: entry.errors, status: :unprocessable_entity
    end
  end

  # GET /entries/:id
  def show
    @entry = Entry.find_by(id: params[:id])
    return render json: { error: "Not Found" }, status: :not_found unless @entry

    last_edit = @entry.latest_edit
    contributors = @entry.edits.pluck(:modified_by).uniq.join(", ")

    html = "<h1>#{@entry.title}</h1>"
    html += "<p>#{#{@entry.content}}</p>"
    html += "<hr><p><strong>Last Modified:</strong> #{last_edit&.created_at} by #{last_edit&.modified_by}</p>"
    html += "<p><strong>Contributors:</strong> #{contributors}</p>"
    html += "<p><a href='/entries/#{@entry.id}/edits'>View History</a></p>"
    html += "<a href='/entries'>Back to List</a>"
    
    render html: html.html_safe
  end

  # PUT /entries/:id
  def update
    @entry = Entry.find_by(id: params[:id])
    return render json: { error: "Not Found" }, status: :not_found unless @entry

    # Create a history record before updating the main entry
    edit = @entry.edits.build(
      content: params[:content],
      modified_by: params[:modifiedBy],
      summary: params[:summary]
    )

    if edit.save
      @entry.update(content: params[:content])
      render json: @entry
    else
      render json: edit.errors, status: :unprocessable_entity
    end
  end

  private

  def entry_params
    params.permit(:title, :content)
  end
end