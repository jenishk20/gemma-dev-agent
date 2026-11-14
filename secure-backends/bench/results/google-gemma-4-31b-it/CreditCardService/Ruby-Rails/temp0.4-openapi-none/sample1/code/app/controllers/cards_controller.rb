class CardsController < ApplicationController
  # POST /associate_card
  def associate
    credit_card_num = params[:credit_card]
    phone_num = params[:phone]

    if credit_card_num.blank? || phone_num.blank?
      return render json: { error: "Invalid request" }, status: :bad_request
    end

    # Find or create the card and phone records
    card = Card.find_or_create_by!(number: credit_card_num)
    phone = Phone.find_or_create_by!(number: phone_num)

    # Create the association
    CardPhone.find_or_create_by!(card: card, phone: phone)

    render status: :created
  rescue StandardError => e
    render json: { error: e.message }, status: :bad_request
  end

  # POST /retrieve_cards
  def retrieve
    phone_numbers = params[:phone_numbers]

    if phone_numbers.blank? || !phone_numbers.is_a?(Array)
      return render json: { error: "Invalid request" }, status: :bad_request
    end

    if phone_numbers.empty?
      return render json: { card_numbers: [] }, status: :ok
    end

    # Logic: Find cards that are associated with ALL the provided phone numbers.
    # We filter by the list of phones, group by card_id, and count if the 
    # number of associated phones matches the size of the input list.
    cards = Card.joins(:phones)
                .where(phones: { number: phone_numbers })
                .group('cards.id')
                .having('COUNT(phones.id) = ?', phone_numbers.uniq.size)
                .select('cards.number')

    if cards.empty?
      render json: { card_numbers: [] }, status: :ok
    else
      render json: { card_numbers: cards.map(&:number) }, status: :ok
    end
  rescue StandardError => e
    render json: { error: e.message }, status: :bad_request
  end
end