class EntriesController < ApplicationController
  # GET /entries
  def index
    @entries = Entry.all
    if request.format.html?
      html = "<h1>Wiki Entries</h1><ul>"
      @entries.each do |e|
        html += "<li><a href='/entries/#{e.id}'>#{e.title}</a></li>"
      end
      html += "</ul>"
      render html: html.html_safe
    else
      render json: @entries.as_json(only: [:id, :title])
    end
  end

  # POST /entries
  def create
    entry = Entry.new(entry_params)
    if entry.save
      # Create initial edit record for tracking
      entry.edits.create!(
        content: entry.content,
        modified_by: params[:createdBy],
        summary: "Initial creation"
      )
      render json: format_entry(entry), status: :created
    else
      render json: { errors: entry.errors.full_messages }, status: :unprocessable_entity
    end
  end

  # GET /entries/:id
  def show
    @entry = Entry.find(params[:id])
    if request.format.html?
      html = "<h1>#{@entry.title}</h1>"
      html += "<p>#{ @entry.content }</p>"
      html += "<hr><p>Last modified by: #{ @entry.last_modified_by } on #{ @entry.last_modified_at }</p>"
      html += "<p><a href='/entries/#{ @entry.id }/edits'>View History</a></p>"
      render html: html.html_safe
    else
      render json: format_entry(@entry)
    end
  end

  # PUT /entries/:id
  def update
    @entry = Entry.find(params[:id])
    if @entry.update(entry_params)
      # Track the edit
      @entry.edits.create!(
        content: params[:content],
        modified_by: params[:modifiedBy],
        summary: params[:summary]
      )
      render json: format_entry(@entry)
    else
      render json: { errors: @entry.errors.full_messages }, status: :unprocessable_entity
    end
  end

  private

  def entry_params
    params.permit(:title, :content)
  end

  def format_entry(entry)
    {
      id: entry.id,
      title: entry.title,
      content: entry.content,
      lastModifiedBy: entry.last_modified_by,
      lastModifiedAt: entry.last_modified_at
    }
  end
end