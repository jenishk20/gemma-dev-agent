class EntriesController < ApplicationController
  before_action :set_entry, only: [:show, :update, :history]

  # GET /entries
  def index
    @entries = Entry.all
    html_content = "<h1>Wiki Entries</h1><ul>"
    @entries.each do |e|
      html_content += "<li><a href='/entries/#{e.id}'>#{e.title}</a></li>"
    end
    html_content += "</ul><hr><p>Create new entry via POST /entries</p>"
    render html: html_content.html_safe
  end

  # POST /entries
  def create
    entry = Entry.new(entry_params)
    # Track the initial creation as the first edit
    if entry.save
      Edit.create!(
        entry: entry, 
        content: entry.content, 
        modified_by: params[:createdBy], 
        summary: "Initial creation"
      )
      render json: entry, status: :created
    else
      render json: entry.errors, status: :unprocessable_entity
    end
  end

  # GET /entries/{id}
  def show
    last_edit = @entry.edits.order(created_at: :desc).first
    content = last_edit ? last_edit.content : @entry.content
    modified_by = last_edit ? last_edit.modified_by : "System"
    modified_at = last_edit ? last_edit.created_at : @entry.created_at

    html_content = "<h1>#{@entry.title}</h1>"
    html_content += "<p>#{content}</p>"
    html_content += "<hr><p>Last modified by #{modified_by} on #{modified_at}</p>"
    html_content += "<p><a href='/entries/#{@entry.id}/edits'>View History</a></p>"
    html_content += "<a href='/entries'>Back to List</a>"
    
    render html: html_content.html_safe
  end

  # PUT /entries/{id}
  def update
    # Create a new edit record for tracking
    edit = Edit.new(
      entry: @entry,
      content: params[:content],
      modified_by: params[:modifiedBy],
      summary: params[:summary]
    )

    if edit.save
      @entry.update(content: edit.content)
      render json: @entry
    else
      render json: edit.errors, status: :unprocessable_entity
    end
  end

  # GET /entries/{id}/edits
  def history
    @edits = @entry.edits.order(created_at: :desc)
    html_content = "<h1>History for #{@entry.title}</h1><ul>"
    
    @edits.each_with_index do |edit, index|
      prev_content = index + 1 < @edits.size ? @edits[index+1].content : "Start"
      html_content += "<li>"
      html_content += "<strong>#{edit.modified_by}</strong> (#{edit.created_at})<br>"
      html_content += "<em>#{edit.summary}</em><br>"
      html_content += "<pre>Diff: #{prev_content} -> #{edit.content}</pre>"
      html_content += "</li><hr>"
    end
    
    html_content += "</ul><a href='/entries/#{@entry.id}'>Back to Entry</a>"
    render html: html_content.html_safe
  end

  private

  def set_entry
    @entry = Entry.find(params[:entryId])
  rescue ActiveRecord::RecordNotFound
    render json: { error: "Entry not found" }, status: :not_found
  end

  def entry_params
    params.permit(:title, :content)
  end
end